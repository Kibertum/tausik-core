"""`xargs` ИСПОЛНЯЕТ то, что ему передали, и гейт записи этого не видел.

ЗАМЕР ДО ПРАВКИ (смена #238, живой парсер). Одна и та же запись, с обёрткой и
без:

    sh -c "echo x > zzz.txt"                    ->  ['zzz.txt']   ловится
    echo hi | xargs -0 sh -c "cat > zzz.txt"    ->  []            ДЫРА
    echo a  | xargs -I{} cp src.txt zzz.txt     ->  []            ДЫРА
    echo x  | xargs tee zzz.txt                 ->  []            ДЫРА

Шесть форм, все с уверенностью `parsed`: гейт не догадывался, он уверенно НЕ
ВИДЕЛ команды. Направление ошибки — ДЫРА, а не ложный блок, и это меняет, что
здесь надо доказывать: починка РАСШИРЯЕТ обнаружение, поэтому опасная сторона —
ложные блоки, и матрица безвредных команд важнее списка закрытых дыр.

ПОЧЕМУ НЕ НОВЫЙ МЕХАНИЗМ. `xargs` — обёртка того же рода, что `env`, `sudo`,
`timeout`: она снимается, и дальше начинается обычная команда, которую разбирают
обычными правилами. Уже закрытая command-prefix-hides-shell-wrapper построила
для этого таблицу `_WRAPPER_VALUE_FLAGS`; `xargs` в неё добавлен, а не обойдён
сбоку. Второй механизм рядом с первым разошёлся бы с ним молча.

ЧТО ОСТАЁТСЯ НЕДОСТУПНЫМ, И ЧЕМ ЭТО НЕ ПОХОЖЕ НА `$VAR`. Что именно запишет
`xargs -I{} sh -c "echo x > {}"`, зависит от ПОТОКА, а поток парсеру недоступен.
Первая редакция теста требовала отфильтровать `{}` по аналогии с нераскрытой
переменной — и аналогия оказалась ложной, что показал прогон: `echo x > $VAR/f`
даёт [] и команда ПРОХОДИТ, потому что неизвестно даже, есть ли запись. Здесь
запись ТОЧНО есть, неизвестно только куда. Отфильтровать `{}` значило бы
пропустить её, то есть открыть дыру ровно там, где эта задача её закрывает.

Поэтому цель остаётся нерезолвимой и команда УПИРАЕТСЯ в гейт. Для надзорного
гейта это верная сторона: неизвестная запись обязана требовать задачи, а не
проходить молча.
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

import bash_cmd_norm as norm  # noqa: E402
import bash_write_parse as bwp  # noqa: E402
from conftest import canonical_ddl  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/hooks/"]

#: Формы, которые ПИШУТ и до правки были невидимы.
HIDDEN_WRITES = (
    pytest.param("echo x | xargs tee zzz.txt", id="tee"),
    pytest.param("echo a | xargs -I{} cp src.txt zzz.txt", id="replace_glued"),
    pytest.param("echo a | xargs -I {} cp src.txt zzz.txt", id="replace_detached"),
    pytest.param('echo hi | xargs -0 sh -c "cat > zzz.txt"', id="null_delimited_shell"),
    pytest.param('echo hi | xargs -n1 -P4 sh -c "echo x > zzz.txt"', id="parallel_shell"),
    pytest.param('echo a | xargs --replace=X sh -c "echo y > zzz.txt"', id="long_flag_with_value"),
    pytest.param("echo a | xargs -i cp src.txt zzz.txt", id="optional_arg_flag_eats_nothing"),
    pytest.param("echo a | xargs -a list.txt cp src.txt zzz.txt", id="arg_file"),
)

#: Команды с `xargs`, которые НИЧЕГО не пишут. Ни одна не имеет права
#: покраснеть: расширение обнаружения оплачивается ложными блоками, и это цена,
#: которую эта правка платить не должна.
HARMLESS = (
    pytest.param("ls | xargs grep foo", id="grep"),
    pytest.param("echo a | xargs echo", id="echo"),
    pytest.param("xargs --help", id="help"),
    pytest.param("find . -name '*.py' | xargs wc -l", id="wc"),
)


@pytest.fixture(scope="module")
def hook_project(tmp_path_factory):
    """The test's own project (`.tausik/tausik.db`, one closed task, nothing
    active): Rule 1 is then the verdict on any in-tree write. Against THIS
    repository the verdict depended on the machine — no database on a CI clone
    meant "allow" (session #254; same fix as test_prose_arguments…)."""
    root = tmp_path_factory.mktemp("xargs_hook_project")
    (root / ".tausik").mkdir()
    conn = sqlite3.connect(str(root / ".tausik" / "tausik.db"))
    conn.execute(canonical_ddl("tasks"))
    conn.execute(
        "INSERT INTO tasks (slug, title, status, created_at, updated_at) "
        "VALUES ('closed', 'closed', 'done', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
    )
    conn.commit()
    conn.close()
    return root


def _hook_blocks(project_dir, command: str) -> bool:
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


class TestДыраЗакрыта:
    """AC-2. Команда за xargs разбирается теми же правилами, что и любая другая."""

    @pytest.mark.parametrize("command", HIDDEN_WRITES)
    def test_парсер_видит_цель(self, command):
        targets, confidence = bwp.write_targets_with_confidence(command)
        assert "zzz.txt" in targets, f"запись невидима: {command!r} -> {targets}"
        assert confidence == "parsed"

    @pytest.mark.parametrize("command", HIDDEN_WRITES[:4])
    def test_живой_хук_блокирует(self, hook_project, command):
        assert _hook_blocks(hook_project, command), f"хук пропустил настоящую запись: {command!r}"

    def test_та_же_команда_без_xargs_ловилась_и_раньше(self):
        """Предпосылка: дыру создавала именно обёртка, а не сама команда."""
        assert bwp.write_targets_with_confidence('sh -c "echo x > zzz.txt"')[0] == ["zzz.txt"]


class TestРасширениеНеСталоЛожнымБлоком:
    """AC-5, и в этом файле она главная. Починка расширяет обнаружение, значит
    опасная сторона — безвредные команды."""

    @pytest.mark.parametrize("command", HARMLESS)
    def test_парсер_не_выдумывает_цели(self, command):
        targets, _c = bwp.write_targets_with_confidence(command)
        assert targets == [], f"фантом на безвредной команде: {command!r} -> {targets}"

    @pytest.mark.parametrize("command", HARMLESS)
    def test_живой_хук_не_блокирует(self, hook_project, command):
        assert not _hook_blocks(hook_project, command), f"ложный блок: {command!r}"

    def test_слово_xargs_в_прозе_аргумента_не_обёртка(self):
        """`xargs` внутри закавыченного аргумента — данные. Проверяется вместе
        с починкой экранирования из соседней задачи: одно правило не имеет права
        отменять другое."""
        command = '.tausik/tausik task log slug "разобрать, как xargs -I{} cp a zzz.txt работает"'
        assert bwp.write_targets_with_confidence(command)[0] == []


class TestФлагиОтделеныОтКоманды:
    """AC-3. Приняв аргумент флага за команду, разбор уедет мимо, и дыра
    останется — а зелёный тест скажет, что её нет."""

    def test_флаг_с_обязательным_значением_съедает_своё_значение(self):
        assert norm._strip_prefixes(["xargs", "-n", "1", "cp", "a", "zzz.txt"])[0] == "cp"

    def test_флаг_без_значения_съедает_только_себя(self):
        assert norm._strip_prefixes(["xargs", "-0", "cp", "a", "zzz.txt"])[0] == "cp"

    def test_флаг_с_НЕОБЯЗАТЕЛЬНЫМ_значением_не_съедает_команду(self):
        """GNU даёт `-i`, `-e` и `-l` необязательный аргумент, который на
        практике пишут слитно. Внеси их в таблицу — и `xargs -i cp` прочитает
        `cp` как значение флага, уйдёт мимо команды и ослепнет. Это та самая
        сторона, в которую таблица двигаться не смеет (память #524)."""
        assert norm._strip_prefixes(["xargs", "-i", "cp", "a", "zzz.txt"])[0] == "cp"

    def test_ни_один_флаг_с_необязательным_значением_не_попал_в_таблицу(self):
        optional = {"-e", "-i", "-l"}
        assert not (norm._WRAPPER_VALUE_FLAGS["xargs"] & optional), (
            "флаг с необязательным аргументом в таблице значений — прямой путь ослепнуть"
        )


class TestМутации:
    """AC-6."""

    def test_без_xargs_в_таблице_дыра_возвращается(self, monkeypatch):
        table = dict(norm._WRAPPER_VALUE_FLAGS)
        table.pop("xargs")
        monkeypatch.setattr(norm, "_WRAPPER_VALUE_FLAGS", table)
        monkeypatch.setattr(norm, "_TRANSPARENT_PREFIXES", frozenset(table))
        assert bwp.write_targets_with_confidence("echo x | xargs tee zzz.txt")[0] == []

    def test_без_xargs_в_таблице_обычная_обёртка_всё_равно_работает(self, monkeypatch):
        """Обратная сторона мутации: снятие починки не должно ЛОМАТЬ остальное,
        иначе тест выше зеленел бы от поломки, а не от отсутствия правки."""
        table = dict(norm._WRAPPER_VALUE_FLAGS)
        table.pop("xargs")
        monkeypatch.setattr(norm, "_WRAPPER_VALUE_FLAGS", table)
        monkeypatch.setattr(norm, "_TRANSPARENT_PREFIXES", frozenset(table))
        assert bwp.write_targets_with_confidence("sudo tee zzz.txt")[0] == ["zzz.txt"]


class TestНедоступноеОбъявлено:
    """AC-4. Что зависит от ПОТОКА, парсеру не видно, и это сказано вслух."""

    def test_подстановка_остаётся_целью_и_команда_упирается(self, hook_project):
        """`xargs -I{} sh -c "echo x > {}"` пишет туда, что придёт из stdin.

        ПЕРВОЕ УТВЕРЖДЕНИЕ ЭТОГО ТЕСТА БЫЛО НЕВЕРНЫМ, и замер это показал. Он
        требовал, чтобы `{}` вообще не попадало в цели — по аналогии с `$VAR`,
        который отфильтрован как объявленный остаток. Но аналогия ложная и
        сравнение стоит рядом: `echo x > $SCRATCH/f` даёт [] и команда
        ПРОХОДИТ, тогда как здесь запись ТОЧНО есть, неизвестно только куда.
        Отфильтровать `{}` значило бы пропустить её — то есть открыть дыру
        ровно там, где эта задача её закрывает.

        Поэтому свойство другое: цель остаётся нерезолвимой, и команда УПИРАЕТСЯ
        в гейт. Для надзорного гейта это верное направление: неизвестная запись
        обязана требовать задачи, а не проходить молча.
        """
        targets, confidence = bwp.write_targets_with_confidence(
            'echo a | xargs -I{} sh -c "echo x > {}"'
        )
        assert targets == ["{}"], "запись стала невидимой — это дыра, а не аккуратность"
        assert confidence == "parsed"
        assert _hook_blocks(hook_project, 'echo a | xargs -I{} sh -c "echo x > {}"'), (
            "неизвестная запись обязана упираться, а не проходить"
        )

    def test_нераскрытая_переменная_по_прежнему_остаток_а_не_цель(self):
        """Граница рядом, и она НЕ трогается этой правкой: `$VAR` остаётся
        объявленным остатком. Два похожих случая расходятся по одному признаку —
        есть ли запись вообще."""
        assert bwp.write_targets_with_confidence("echo x > $SCRATCH/f")[0] == []

    def test_остаток_назван_в_исходнике(self):
        """Не в задаче и не в changelog — там, где его прочтёт следующий,
        кто будет трогать таблицу."""
        with open(
            os.path.join(_REPO, "scripts", "hooks", "bash_cmd_norm.py"), encoding="utf-8"
        ) as fh:
            source = fh.read()
        assert "STDIN" in source and "xargs" in source
