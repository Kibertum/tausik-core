"""Ноль мёртвых СИМВОЛОВ, и это удерживается, а не убрано однажды.

ЧТО УЖЕ БЫЛО И ЧЕГО НЕ ХВАТАЛО. `audit_unused_python` отвечает на вопрос «какой
МОДУЛЬ никто не импортирует» и на этом дереве даёт ноль. Вопрос «какая ФУНКЦИЯ,
КЛАСС или КОНСТАНТА определена и не упоминается больше нигде» не задавал никто, и
ответ на него был 14.

САМЫЕ ДОРОГИЕ ИЗ ЧЕТЫРНАДЦАТИ — те, что ВЫГЛЯДЕЛИ ЖИВЫМИ. Четыре функции в
`harness/claude/mcp/brain/handlers.py` носили имена четырёх MCP-инструментов
(`handle_brain_store_pattern` и соседи), а диспетчер `handle_tool` направлял эти
инструменты через `_handle_store` и именованные функции не звал. Читатель,
открывший файл, правил бы код, который не исполняется.

КАСКАД. Удаление двух точек входа в `bootstrap` обнажило восемь функций, которые
звали только они, а те — ещё одну константу. `bootstrap/generator.py` оказался
мёртвым ЦЕЛИКОМ и удалён. Ровно поэтому проверка нужна повторяемая: одна уборка
не заканчивает работу, она её открывает.

ДВЕ ЛОВУШКИ ПРИ НАПИСАНИИ ТАКОГО СКАНЕРА, обе стоили ошибок в этой же смене и
обе — в РАЗНЫЕ стороны:

  * НЕ ИСКЛЮЧИТЬ `.tausik/` — упоминания внутри venv и рабочего состояния
    засчитываются за ссылки, и сканер показывает дерево ЧИЩЕ, чем оно есть.
    Стоило трёх пропущенных символов.
  * СЧИТАТЬ СОБСТВЕННЫЕ УПОМИНАНИЯ ПО ОДНОМУ ФАЙЛУ. Приватный помощник с одним и
    тем же именем живёт в НЕСКОЛЬКИХ модулях — `_now_iso` в двух, `_cmd_list` в
    двух, `_LABEL` в пяти. Вычесть из occurrences одного файла общее число
    определений по всем — значит увести счёт в минус и не засчитать попадание
    никогда. Черновик так и делал и объявил мёртвыми 13 ЖИВЫХ имён; поверивший
    ему удалил бы работающий код. Поэтому `own` ниже суммируется по ВСЕМ файлам,
    где имя определено.

ЧТО ВЫЧТЕНО ЯВНО, потому что зовётся не по имени: `test_*` и `Test*` (pytest),
`pytest_*` (хуки), `cmd_*` (таблица диспетчеризации CLI), дандеры, `main`/`run`.
Вычитание объявлено здесь, а не спрятано в регулярном выражении: проверка,
которая молча прощает целые классы имён, показывает более чистое дерево, чем
измерила.
"""

from __future__ import annotations

import ast
import collections
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

CROSSCUTTING_SCOPE = ["scripts/", "bootstrap/", "harness/"]

pytestmark = pytest.mark.slow

#: Где ищем ОПРЕДЕЛЕНИЯ.
_ROOTS = ("scripts", "bootstrap", "harness")

#: Куда не заглядываем. Развёрнутые копии профилей — КОПИИ, а не ссылки: считать
#: их упоминанием значило бы объявить живым всё, что туда скопировано.
_SKIP_DIRS = {"__pycache__", ".git", "node_modules", "venv", ".venv"}
_PROFILES = {".claude", ".cursor", ".qwen", ".kilo", ".opencode", ".tausik"}

#: Имена, которые зовут НЕ ПО ИМЕНИ. Список объявлен, а не выведен.
_CALLED_BY_CONVENTION = re.compile(r"^(test_|Test[A-Z]|pytest_|cmd_|__|main$|run$)")

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _defined() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for root in _ROOTS:
        for path in (_REPO / root).rglob("*.py"):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            rel = path.relative_to(_REPO).as_posix()
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    found.setdefault(node.name, []).append(f"{rel}:{node.lineno}")
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            found.setdefault(target.id, []).append(f"{rel}:{node.lineno}")
    return found


def _mentions() -> tuple[collections.Counter, dict[str, collections.Counter]]:
    """Одним проходом по дереву: сколько раз каждое слово вообще встречается."""
    total: collections.Counter = collections.Counter()
    per_file: dict[str, collections.Counter] = {}
    for pattern in ("*.py", "*.json", "*.md", "*.toml", "*.yml", "*.yaml", "*.js"):
        for path in _REPO.rglob(pattern):
            parts = path.relative_to(_REPO).parts
            if any(p in _SKIP_DIRS for p in parts) or (parts and parts[0] in _PROFILES):
                continue
            try:
                counted = collections.Counter(_WORD.findall(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue
            per_file[path.relative_to(_REPO).as_posix()] = counted
            total.update(counted)
    return total, per_file


def _dead() -> list[str]:
    defined = _defined()
    total, per_file = _mentions()
    dead: list[str] = []
    for name, places in sorted(defined.items()):
        if _CALLED_BY_CONVENTION.match(name):
            continue
        homes = {p.split(":")[0] for p in places}
        own = sum(per_file.get(home, collections.Counter()).get(name, 0) for home in homes)
        if total.get(name, 0) - own <= 0 and own <= len(places):
            dead.append(f"{places[0]}  {name}")
    return dead


class TestНиОдногоМёртвогоСимвола:
    def test_дерево_чисто(self):
        dead = _dead()
        assert not dead, "определены и не упоминаются больше нигде:\n  " + "\n  ".join(dead)

    def test_проверка_действительно_смотрит_на_дерево(self):
        """Предпосылка. Ноль мёртвых при нуле осмотренных символов — самый тихий
        способ обессмыслить проверку выше."""
        assert len(_defined()) > 2_000

    def test_охрана_умеет_покраснеть(self, tmp_path, monkeypatch):
        """Отрицательная половина: подсовывается символ, которого никто не
        зовёт, и проверка обязана его назвать."""
        defined = {"НикемНеЗовомый": ["scripts/выдумка.py:1"]}
        monkeypatch.setattr(sys.modules[__name__], "_defined", lambda: defined)
        assert any("НикемНеЗовомый" in row for row in _dead())


class TestВычитаемоеОбъявлено:
    """Проверка, молча прощающая классы имён, показывает более чистое дерево,
    чем измерила. Поэтому вычитаемое проверяется отдельно."""

    @pytest.mark.parametrize(
        "name",
        [
            pytest.param("test_something", id="pytest_function"),
            pytest.param("TestSomething", id="pytest_class"),
            pytest.param("pytest_sessionfinish", id="pytest_hook"),
            pytest.param("cmd_graph", id="cli_dispatch_table"),
            pytest.param("main", id="entry_point"),
        ],
    )
    def test_имя_вызываемое_по_соглашению_вычитается(self, name):
        assert _CALLED_BY_CONVENTION.match(name)

    @pytest.mark.parametrize(
        "name",
        [
            pytest.param("handle_brain_store_pattern", id="mcp_handler"),
            pytest.param("analyze_project", id="ordinary_function"),
            pytest.param("VALID_EPIC_STATUSES", id="constant"),
        ],
    )
    def test_обычное_имя_не_вычитается(self, name):
        """Все три — из тех четырнадцати. Если бы регулярное выражение их
        прощало, уборка была бы пустой."""
        assert not _CALLED_BY_CONVENTION.match(name)


class TestИмяИзНесколькихМодулейНеСчитаетсяМёртвым:
    """Вторая ловушка, проверенная на НАСТОЯЩИХ именах этого дерева.

    Приватные помощники повторяются между модулями по совершенно законным
    причинам: `_cmd_list` — обработчик подкоманды `list` у нескольких групп
    команд, `_LABEL` — метка колонки у нескольких отчётов. Сканер, считающий
    собственные упоминания по одному файлу, объявляет их мёртвыми — и это
    ошибка в опасную сторону: поверивший удалит работающий код.
    """

    @pytest.mark.parametrize(
        "name",
        [
            pytest.param("_cmd_list", id="two_modules"),
            # `_now_iso` stood here until the Notion removal left it in one
            # module (session #253); the premise is re-checked by the first
            # assert, so the name must be one the live tree still repeats.
            pytest.param("_load_config_safe", id="three_modules_helper"),
            pytest.param("_LABEL", id="five_modules"),
            pytest.param("_validate_gates", id="two_modules_validator"),
        ],
    )
    def test_живое_имя_из_нескольких_модулей_не_попадает_в_мёртвые(self, name):
        defined = _defined()
        assert len(defined.get(name, [])) >= 2, (
            f"{name} больше не определено в нескольких модулях — предпосылка "
            "теста исчезла, и он проверяет не то"
        )
        assert not any(row.endswith(f"  {name}") for row in _dead())
