"""Экранированная и закавыченная стрелка — данные, а не перенаправление.

НАЙДЕНО ЖИВЬЁМ, смена #211: гейт записи заблокировал команду подсчёта задач
`if [ "$d" \\> "2026-09-04T11:30:36Z" ]; then ... fi`, объявив целью записи
СТРОКУ С ДАТОЙ. Никакой записи в команде нет. Уверенность разбора при этом была
`parsed` — то есть гейт не догадывался, он уверенно прочитал данные как команду.

КОРЕНЬ, ЗАМЕРЕННЫЙ В СМЕНЕ #238. `tokenize` зовёт shlex с `posix=True` — то, что
делает `"a b"` одним токеном, — и тот же проход снимает кавычки и разрешает
экранирование. После него `\\>`, `">"` и настоящий `>` суть один и тот же токен.
Свидетельство, отделяющее данные от команды, остаётся только в ИСХОДНОМ ТЕКСТЕ:

    [ "$a" \\> "zzz.txt" ]     ->  ['zzz.txt']  сравнение, не запись
    echo a ">" b.txt          ->  ['b.txt']    закавыченный литерал
    echo a > b.txt            ->  ['b.txt']    НАСТОЯЩАЯ ЗАПИСЬ

ЧТО ЭТОТ ФАЙЛ ОХРАНЯЕТ И В КАКУЮ СТОРОНУ. Починка есть СУЖЕНИЕ блокирующего
гейта надзора, то есть движение в сторону разрешения, — самая опасная форма
правки. Поэтому матрица настоящих перенаправлений здесь ВАЖНЕЕ списка фантомов:
ни одна её клетка не имеет права стать зелёной. Обе половины гоняются через
ЖИВОЙ ХУК, а не только через парсер, потому что блокирует хук.

ЧЕГО ЗДЕСЬ НЕТ НАМЕРЕННО. Ничего про политику доверия к `regex_fallback`.
Команда, которая не токенизируется вовсе, — отдельный вопрос (блокировать ли по
догадке), он решается владельцем и этой правкой не тронут: все семь строк выше
имеют уверенность `parsed`.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_REPO, "scripts"), os.path.join(_REPO, "scripts", "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argument_data as ad  # noqa: E402
import bash_write_parse as bwp  # noqa: E402
from conftest import canonical_ddl  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/hooks/"]

#: Формы, где `<`/`>` заведомо НЕ перенаправление. Каждая проверена против
#: настоящего bash: ни одна из них не создаёт файла.
NOT_A_WRITE = (
    pytest.param('if [ "$d" \\> "2026-09-04T11:30:36Z" ]; then echo yes; fi', id="incident_211"),
    pytest.param('[ "$a" \\> "zzz.txt" ]', id="bracket_escaped"),
    pytest.param('[[ "$a" > "zzz.txt" ]]', id="double_bracket"),
    pytest.param('test "$a" \\> "zzz.txt"', id="test_builtin_escaped"),
    pytest.param("echo a \\> b.txt", id="escaped_literal"),
    pytest.param('echo a ">" b.txt', id="quoted_literal"),
    pytest.param("echo 'a > b.txt'", id="single_quoted"),
)

#: Матрица настоящих записей. Ни одна клетка не имеет права позеленеть.
IS_A_WRITE = (
    pytest.param("echo hi > zzz.txt", id="plain"),
    pytest.param("echo hi >> zzz.txt", id="append"),
    pytest.param("cmd 2> zzz.txt", id="stderr"),
    pytest.param("cmd &> zzz.txt", id="both_streams"),
    pytest.param("echo hi>zzz.txt", id="no_space"),
    pytest.param("if [ 1 = 1 ]; then echo hi > zzz.txt; fi", id="inside_if_body"),
    pytest.param("( echo hi > zzz.txt )", id="subshell"),
    pytest.param('env FOO=1 sh -c "echo hi > zzz.txt"', id="behind_wrapper"),
    pytest.param('[[ "$a" = b ]] > zzz.txt', id="after_the_double_bracket_span"),
    pytest.param('[ "$a" > "zzz.txt" ]', id="single_bracket_unescaped_bash_redirects_here"),
    pytest.param("echo hi | tee zzz.txt", id="tee"),
    pytest.param("cp a.txt zzz.txt", id="cp_trailing_positional"),
)


@pytest.fixture(scope="module")
def hook_project(tmp_path_factory):
    """A project of the test's OWN: `.tausik/tausik.db` with one closed task
    and nothing active, so Rule 1 is the verdict on any in-tree write.

    The first version ran the hook against THIS repository — and the verdict
    then depended on the machine: a CI clone after `bootstrap --no-detect` has
    no database, so the hook allowed everything and twelve "still blocks" cases
    went red on the runner (session #251); on a developer machine an active
    task without `scope_paths` would have flipped them the same way. A test
    about the hook must not read somebody else's project state.
    """
    root = tmp_path_factory.mktemp("prose_hook_project")
    tausik = root / ".tausik"
    tausik.mkdir()
    conn = sqlite3.connect(str(tausik / "tausik.db"))
    conn.execute(canonical_ddl("tasks"))
    conn.execute(
        "INSERT INTO tasks (slug, title, status, created_at, updated_at) "
        "VALUES ('closed', 'closed', 'done', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
    )
    conn.commit()
    conn.close()
    return root


def _hook_blocks(project_dir, command: str) -> bool:
    """Живой хук на настоящем вводе. Парсер может быть прав, а хук — нет."""
    payload = json.dumps(
        {"tool_name": "Bash", "session_id": "t", "tool_input": {"command": command}}
    )
    result = subprocess.run(
        [sys.executable, os.path.join(_REPO, "scripts", "hooks", "bash_write_gate.py")],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(project_dir),
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "TAUSIK_SKIP_HOOKS": "",
        },
        timeout=120,
    )
    return result.returncode != 0


class TestДанныеНеСтановятсяПеренаправлением:
    """AC-3. Семь форм, в которых автор написал символ КАК ДАННЫЕ."""

    @pytest.mark.parametrize("command", NOT_A_WRITE)
    def test_парсер_не_видит_цели(self, command):
        targets, confidence = bwp.write_targets_with_confidence(command)
        assert targets == [], f"фантом {targets} с уверенностью {confidence}"
        assert confidence == "parsed", (
            "уверенность деградировала — значит зелёное получено отказом читать, "
            "а не пониманием, и это другое утверждение"
        )

    @pytest.mark.parametrize("command", NOT_A_WRITE[:4])
    def test_живой_хук_не_блокирует(self, hook_project, command):
        assert not _hook_blocks(hook_project, command)


class TestДыраНеОткрыта:
    """AC-4, и в этом файле она важнее всего остального.

    Правка движется в сторону РАЗРЕШЕНИЯ. Значит доказывать её надо с другой
    стороны: настоящее перенаправление в настоящей команде обязано ловиться
    по-прежнему, включая формы, соседствующие с починенными.
    """

    @pytest.mark.parametrize("command", IS_A_WRITE)
    def test_парсер_по_прежнему_видит_цель(self, command):
        targets, _c = bwp.write_targets_with_confidence(command)
        assert "zzz.txt" in targets, f"настоящая запись перестала ловиться: {command!r}"

    @pytest.mark.parametrize("command", IS_A_WRITE)
    def test_живой_хук_по_прежнему_блокирует(self, hook_project, command):
        assert _hook_blocks(hook_project, command), f"хук пропустил настоящую запись: {command!r}"

    def test_одиночная_скобка_намеренно_не_освобождена(self):
        """`[` — обычная команда, и bash ДЕЙСТВИТЕЛЬНО читает `[ a > b ]` как
        перенаправление; ради этого идиома и требует `\\>`. `[[` — грамматика,
        внутри неё перенаправлений нет вовсе. Разница не недосмотр: освободить
        `[` значило бы разойтись с bash в сторону разрешения."""
        assert bwp.write_targets_with_confidence('[ "$a" > "zzz.txt" ]')[0] == ["zzz.txt"]
        assert bwp.write_targets_with_confidence('[[ "$a" > "zzz.txt" ]]')[0] == []


class TestМутации:
    """AC-6. Снятие починки обязано вернуть фантомы, и ни одна мутация не
    ДОБАВЛЯЕТ проверку (память #503)."""

    def test_без_маски_фантомы_возвращаются(self, monkeypatch):
        monkeypatch.setattr(bwp, "mask_quoted_operators", lambda text: text)
        targets, confidence = bwp.write_targets_with_confidence("echo a \\> b.txt")
        assert targets == ["b.txt"], "маска ничего не делала — тест выше зелен по другой причине"
        assert confidence == "parsed"

    def test_без_маски_настоящая_запись_всё_равно_ловится(self, monkeypatch):
        """Обратная сторона мутации: снятие починки не должно ЛОМАТЬ ловлю —
        иначе первый тест зеленел бы от поломки, а не от починки."""
        monkeypatch.setattr(bwp, "mask_quoted_operators", lambda text: text)
        assert bwp.write_targets_with_confidence("echo hi > zzz.txt")[0] == ["zzz.txt"]


class TestНезакрытаяКавычкаНеДелаетГейтСлабее:
    """AC-8(г). Fail-soft: вход, который разбор прочесть не может, обязан
    оставить гейт НЕ СЛАБЕЕ прежнего.

    Маска отказывается переписывать текст с незакрытой кавычкой и возвращает
    его как есть. Иначе она могла бы замаскировать оператор в половине команды,
    которую всё равно не понимает, — единственная правка здесь, способная
    СПРЯТАТЬ настоящую запись.
    """

    def test_незакрытая_кавычка_возвращается_нетронутой(self):
        broken = 'echo "unterminated > zzz.txt'
        assert ad.mask_quoted_operators(broken) == broken

    def test_такая_команда_по_прежнему_даёт_цель(self):
        targets, confidence = bwp.write_targets_with_confidence('echo "unterminated > zzz.txt')
        assert "zzz.txt" in targets
        assert confidence == "regex_fallback", (
            "уверенность обязана честно назвать себя догадкой — политика доверия "
            "к догадке решается отдельно и этой правкой не тронута"
        )


class TestПоверхностьНазвана:
    """AC-8(а,б). Что именно перестало считаться целью, и можно ли за этим
    спрятать настоящую запись."""

    def test_маска_трогает_только_операторы_перенаправления(self):
        assert ad.OPERATOR_CHARS == "<>", (
            "поверхность расширилась: каждый новый символ — это ещё один способ "
            "написать команду там, где парсер теперь видит данные"
        )

    def test_снаружи_кавычек_и_без_экранирования_ничего_не_маскируется(self):
        """Противник рассмотрен структурой, а не примером: чтобы спрятать запись,
        её оператор пришлось бы закавычить или экранировать — а тогда оболочка
        его тоже не исполнит. Спрятать МОЖНО только то, что и так не выполнится."""
        assert ad.mask_quoted_operators("echo hi > f") == "echo hi > f"

    def test_метка_восстанавливается_и_не_течёт_наружу(self):
        masked = ad.mask_quoted_operators('echo ">" f')
        assert masked != 'echo ">" f'
        assert ad.unmask(masked) == 'echo ">" f'
        for target in bwp.write_targets_with_confidence('echo ">" f.txt')[0]:
            assert all(ord(ch) < 0xE000 or ord(ch) > 0xF8FF for ch in target), (
                f"метка утекла в цель: {target!r}"
            )
