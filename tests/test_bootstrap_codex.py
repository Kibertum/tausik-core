"""Хуки Codex обязаны СРАБАТЫВАТЬ, а не выглядеть подключёнными.

ЧТО БЫЛО НАЙДЕНО (смена #241). В проекте лежал `.codex/hooks.json` — не наш,
bootstrap его не создавал, потому что `codex` отсутствовал в `SCAFFOLD_IDES`.
Двадцать четыре команды, и каждая вида
``python -X utf8 ${CLAUDE_PROJECT_DIR}/.claude/scripts/hooks/<имя>.py``.

Строки `CLAUDE_PROJECT_DIR` в бинаре Codex НЕТ — проверено там же, где найдено
наличие `hooks.json`, `PreToolUse` и `permissionDecision`. Переменная
раскрывается в пустоту, путь становится `/.claude/scripts/hooks/task_gate.py` и
не находится. Под Codex молча не работал ни один гейт: ни Rule 1, ни ACL области,
ни firewall, ни сканер секретов.

ПОЭТОМУ ГЛАВНЫЙ ТЕСТ ФАЙЛА — `TestНиОднойНераскрываемойПеременной`, и он
проверяет ОТСУТСТВИЕ, а не наличие. Проверка «файл сгенерирован» была зелёной и
на сломанном файле: он тоже существовал, тоже был валидным JSON и тоже
перечислял все тринадцать гейтов. Отличало его ровно одно — команды не
запускались.

ВТОРАЯ ПОЛОВИНА — ОДИН ИСТОЧНИК НАБОРА. Хосты расходятся не сразу: хук,
добавленный одному, отсутствует у другого несколько релизов, и обнаруживается
это на чужой машине. Поэтому набор берётся из `build_hooks_dict`, а тест
краснеет, если у claude появился хук, которого нет у codex.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _sub in ("scripts", "bootstrap"):
    if str(_REPO / _sub) not in sys.path:
        sys.path.insert(0, str(_REPO / _sub))

import bootstrap_codex  # noqa: E402
from bootstrap_config import IDE_DIRS, SCAFFOLD_IDES  # noqa: E402

CROSSCUTTING_SCOPE = ["bootstrap/"]

#: Живой развёрнутый профиль. Он и есть предмет: дефект был не в том, что
#: генератор пишет плохо, а в том, что на диске лежал файл, который никто не
#: генерировал и никто не проверял.
_LIVE = _REPO / ".codex" / "hooks.json"


def _commands(document: dict) -> list[str]:
    return [
        hook["command"]
        for groups in document.get("hooks", {}).values()
        for entry in groups
        for hook in entry.get("hooks", [])
    ]


def _script_of(command: str) -> str:
    """Путь к скрипту из строки команды `<python> -X utf8 <script> [аргументы]`.

    Берётся токен ПОСЛЕ `utf8`, а не последний: у части хуков есть аргументы и
    оболочечный хвост (`--auto --record 2>&1 || true`), и «последний токен»
    указал бы на слово `true`.
    """
    parts = command.split()
    return parts[parts.index("utf8") + 1] if "utf8" in parts else parts[-1]


@pytest.fixture(scope="module")
def live() -> dict:
    if not _LIVE.is_file():
        pytest.skip("профиль .codex не развёрнут в этом дереве")
    return json.loads(_LIVE.read_text(encoding="utf-8"))


class TestCodexЭтоЦельПервогоКласса:
    """AC-1. Членство в списке — обещание, и оно подкреплено генератором."""

    def test_у_него_есть_каталог_профиля(self):
        assert IDE_DIRS["codex"] == ".codex"

    def test_членство_подкреплено_генератором(self):
        """Ровно та ошибка, на которой обжёгся opencode: документация называла
        его поддержанным, пока генератора не было.

        Само членство в SCAFFOLD_IDES проверяет `test_ide_single_source`, один
        параметризованный тест на все такие хосты; здесь — вторая половина
        обещания, ради которой этот файл и написан.
        """
        assert "codex" in SCAFFOLD_IDES
        assert callable(bootstrap_codex.scaffold_codex)
        source = (_REPO / "bootstrap" / "bootstrap.py").read_text(encoding="utf-8")
        assert 'elif ide == "codex":' in source, "ветка не подключена к run_for_ide"
        assert "scaffold_codex(" in source


class TestНиОднойНераскрываемойПеременной:
    """ГЛАВНЫЙ ТЕСТ ФАЙЛА. Проверяется ОТСУТСТВИЕ: сломанный файл был валидным
    JSON, перечислял все гейты и не запускал ни одного."""

    def test_в_живом_профиле_нет_подстановок(self, live):
        offenders = [c for c in _commands(live) if "${" in c or "%" in c.split()[0]]
        assert not offenders, (
            "команда хука содержит подстановку, которую Codex не раскрывает — "
            "в его бинаре нет ни CLAUDE_PROJECT_DIR, ни CODEX_PROJECT_ROOT, ни "
            "workspaceFolder, и хук молча не запустится:\n  " + "\n  ".join(offenders[:3])
        )

    def test_в_свежесгенерированном_тоже_нет(self, tmp_path):
        built = bootstrap_codex.build_codex_hooks(str(tmp_path / ".codex"))
        assert not [c for c in _commands({"hooks": built}) if "${" in c]

    def test_проверка_поймала_бы_сломанный_файл(self):
        """Отрицательная половина: та же проверка на ТОМ САМОМ содержимом,
        которое лежало на диске. Без неё зелёный тест ничего не значит."""
        broken = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Write",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python -X utf8 ${CLAUDE_PROJECT_DIR}/.claude/scripts/hooks/task_gate.py",
                            }
                        ],
                    }
                ]
            }
        }
        assert [c for c in _commands(broken) if "${" in c]


class TestКаждыйПутьСуществует:
    """AC-2. Существование проверяется на ЖИВОМ дереве: во временном каталоге
    скриптов нет по построению, и там проверка была бы бессодержательной."""

    def test_интерпретатор_и_скрипт_на_месте(self, live):
        missing = [s for s in (_script_of(c) for c in _commands(live)) if not Path(s).is_file()]
        assert not missing, "хук указывает на несуществующий файл:\n  " + "\n  ".join(missing)

    def test_путей_действительно_много(self, live):
        """Предпосылка: пустой список прошёл бы проверку выше молча."""
        assert len(_commands(live)) >= 20


class TestНаборОдинНаДваХоста:
    """AC-5. Хосты расходятся не сразу, а через несколько релизов — и
    обнаруживается это на чужой машине."""

    def test_codex_повторяет_набор_claude_событие_в_событие(self, tmp_path):
        from bootstrap_hooks import build_hooks_dict

        reference = build_hooks_dict(lambda script, suffix="": f"X/{script}{suffix}")
        codex = bootstrap_codex.build_codex_hooks(str(tmp_path / ".codex"))
        assert set(codex) == set(reference), "у codex не тот набор СОБЫТИЙ, что у claude"
        for event in reference:
            assert [e.get("matcher") for e in codex[event]] == [
                e.get("matcher") for e in reference[event]
            ], f"событие {event}: набор матчеров разошёлся"

    def test_каждое_событие_поддержано_хостом(self, live):
        """Хук на событие, которого у хоста нет, — не ложь, но и не гейт.
        Список проверен по бинарю Codex в смене #241."""
        supported = {
            "PreToolUse",
            "PostToolUse",
            "SessionStart",
            "SessionEnd",
            "UserPromptSubmit",
            "Stop",
            "PreCompact",
            "Notification",
            "SubagentStop",
        }
        assert set(live["hooks"]) <= supported


class TestПовторныйПрогонИЧужиеКлючи:
    """AC-4. Идемпотентность по ЗАМЕЩЕНИЮ ключа: набор хуков — снимок текущего
    объявления, и дописывание растило бы его с каждым прогоном."""

    def test_два_прогона_дают_один_файл(self, tmp_path):
        target = tmp_path / ".codex"
        first = Path(bootstrap_codex.generate_codex_hooks(str(tmp_path), str(target)))
        content = first.read_text(encoding="utf-8")
        bootstrap_codex.generate_codex_hooks(str(tmp_path), str(target))
        assert first.read_text(encoding="utf-8") == content

    def test_чужие_ключи_переживают_перезапись(self, tmp_path):
        target = tmp_path / ".codex"
        target.mkdir()
        path = target / "hooks.json"
        path.write_text(
            json.dumps({"hooks": {}, "чужое": {"ключ": 1}, "second": "值"}, ensure_ascii=False),
            encoding="utf-8",
        )
        bootstrap_codex.generate_codex_hooks(str(tmp_path), str(target))
        after = json.loads(path.read_text(encoding="utf-8"))
        assert after["чужое"] == {"ключ": 1}
        assert after["second"] == "值"
        assert after["hooks"], "наш ключ не записан"

    def test_испорченный_файл_заменяется_а_не_роняет_bootstrap(self, tmp_path, capsys):
        """Уронить bootstrap значило бы оставить хост без единого гейта из-за
        одной битой скобки; заменить молча — унести чужие ключи без следа."""
        target = tmp_path / ".codex"
        target.mkdir()
        (target / "hooks.json").write_text("{не json", encoding="utf-8")
        bootstrap_codex.generate_codex_hooks(str(tmp_path), str(target))
        assert "WARNING" in capsys.readouterr().out
        assert json.loads((target / "hooks.json").read_text(encoding="utf-8"))["hooks"]
