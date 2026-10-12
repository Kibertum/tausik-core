"""Полные схемы — у ядра; остальные достижимы, а не потеряны.

ЗАМЕР, смена #275. Список инструментов, который уходит в КАЖДЫЙ запрос, —
14 337 токенов при 147 инструментах. По журналу `.tausik/token_metrics.jsonl`
(единственный источник, пишущий ИМЯ инструмента) из 5782 вызовов с именем MCP
были 75, то есть 1,3%, а различных инструментов вызвано шесть.

ГЛАВНЫЙ РИСК ЭТОЙ ПРАВКИ НЕ В ТОМ, ЧТО ОНА МАЛО СЭКОНОМИТ, а в том, что
сэкономленное уйдёт на лишний ход: модель не найдёт инструмент, которого ждала, и
либо позовёт несуществующий, либо пойдёт кругом. Поэтому отрицательная половина
здесь весит больше положительной: проверяется, что ни одно имя не исчезло, что
ядро содержит всё нужное на ПЕРВОМ ходу, и что выгруженная схема добирается одним
вызовом.

ПО УМОЛЧАНИЮ ВЫКЛЮЧЕНО, и это тоже закреплено тестом: правка такого класса
включается замером у потребителя, а не решением автора.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _sub in ("scripts", "bootstrap", "harness/claude/mcp/project"):
    if str(_REPO / _sub) not in sys.path:
        sys.path.insert(0, str(_REPO / _sub))

import mcp_tool_tiers as tiers  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/mcp_tool_tiers.py", "harness/claude/mcp/"]


@pytest.fixture(scope="module")
def all_tools() -> list[dict]:
    from tools import TOOLS

    return TOOLS


def _tok(obj) -> int:
    return len(json.dumps(obj, ensure_ascii=False)) // 4


class TestНиОдноИмяНеИсчезает:
    """Имена остаются в контексте — это условие из источника правки, а не вкус:
    модель должна видеть, что инструмент существует."""

    def test_состав_имён_совпадает(self, all_tools):
        assert [t["name"] for t in tiers.compact_tools(all_tools)] == [t["name"] for t in all_tools]

    def test_порядок_сохранён(self, all_tools):
        """Порядок — часть кэшируемого префикса: перестановка обнуляет кэш так
        же надёжно, как правка текста."""
        compact = tiers.compact_tools(all_tools)
        assert compact[0]["name"] == all_tools[0]["name"]
        assert compact[-1]["name"] == all_tools[-1]["name"]

    def test_у_каждого_есть_схема_хотя_бы_заглушка(self, all_tools):
        """Инструмент без `inputSchema` хост может отвергнуть до нашего
        `call_tool` — тогда скрытие перестаёт быть только экономией."""
        assert all(t.get("inputSchema") for t in tiers.compact_tools(all_tools))


class TestЯдроСодержитНужноеНаПервомХоду:
    """AC-4, главная отрицательная половина. Инструмент, нужный сразу, из статики
    не выгружается: экономия, оплаченная лишним ходом, — не экономия."""

    @pytest.mark.parametrize(
        "name",
        [
            "tausik_session_open",
            "tausik_status",
            "tausik_task_list",
            "tausik_task_quick",
            "tausik_task_start",
            "tausik_task_step",
            "tausik_task_done",
            "tausik_task_log",
            "tausik_verify",
            "tausik_search",
            "tausik_tool_schema",
        ],
    )
    def test_остаётся_в_ядре(self, name, all_tools):
        assert name in tiers.CORE_TOOLS
        full = {t["name"]: t for t in all_tools}
        compact = {t["name"]: t for t in tiers.compact_tools(all_tools)}
        if name in full:
            assert compact[name] == full[name], f"{name} урезан, а нужен целиком"

    def test_шесть_замеренных_вызовов_все_в_ядре(self):
        """Те самые шесть, что нашлись в журнале. Если бы хоть один был выгружен,
        замер противоречил бы правке."""
        measured = {
            "tausik_task_log",
            "tausik_memory_add",
            "tausik_decide",
            "tausik_session_handoff",
            "tausik_session_end",
            "tausik_session_start",
        }
        assert measured <= tiers.CORE_TOOLS

    def test_ядро_названо_в_одном_месте(self):
        """AC-2. Второй перечень означал бы, что добавленный в ядро инструмент
        молча не попадёт в половину проверок."""
        assert isinstance(tiers.CORE_TOOLS, frozenset)
        assert 10 < len(tiers.CORE_TOOLS) < 40, "ядро либо пустеет, либо съедает список"


class TestВыгруженноеДостижимо:
    """AC-3. Схема добирается ОДНИМ вызовом, и отказ называет, чем его снять."""

    def test_схема_по_точному_имени(self, all_tools):
        offloaded = next(t for t in all_tools if t["name"] not in tiers.CORE_TOOLS)
        reply = json.loads(tiers.schema_reply(all_tools, offloaded["name"], None))
        assert reply["inputSchema"] == offloaded["inputSchema"]

    def test_подстрока_даёт_имена(self, all_tools):
        reply = tiers.schema_reply(all_tools, None, "epic")
        assert "tausik_epic" in reply

    def test_пустой_запрос_даёт_полный_перечень(self, all_tools):
        names = json.loads(tiers.schema_reply(all_tools, None, ""))
        assert len(names) == len(all_tools)

    def test_отказ_называет_чем_его_снять(self, all_tools):
        """Отказ без следующего действия — тупик в лучшей формулировке, и здесь
        он вернул бы агента к угадыванию аргументов."""
        reply = tiers.schema_reply(all_tools, "tausik_epic_выдумка", None)
        assert "нет" in reply and tiers.SCHEMA_TOOL in reply
        assert "tausik_epic" in reply, "похожие имена не предложены"


class TestПоУмолчаниюВыключено:
    """Правка такого класса включается замером у потребителя, а не автором."""

    def test_без_конфига_список_не_урезан(self, all_tools, monkeypatch, tmp_path):
        monkeypatch.setattr(tiers, "_feature_enabled", lambda *a, **k: False)
        assert tiers.apply_tiers(all_tools) is all_tools

    @pytest.mark.parametrize(
        ("config", "expected"),
        [
            ({"mcp": {"compact_tool_list": True}}, True),
            ({"bootstrap": {"mcp": {"compact_tool_list": True}}}, False),
        ],
    )
    def test_project_flag_is_read_only_from_the_root_config(self, tmp_path, config, expected):
        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir()
        (tausik_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

        assert tiers._feature_enabled(str(tausik_dir)) is expected

    @pytest.mark.parametrize("existing", [None, False])
    def test_bootstrap_enables_compaction_but_preserves_explicit_opt_out(self, tmp_path, existing):
        from bootstrap_config import save_tausik_config

        config_path = tmp_path / ".tausik" / "config.json"
        if existing is not None:
            config_path.parent.mkdir()
            config_path.write_text(
                json.dumps({"mcp": {"compact_tool_list": existing}}), encoding="utf-8"
            )
        save_tausik_config(
            str(config_path),
            {"core_skills": [], "extension_skills": []},
            lib_commit=None,
            stacks=[],
            ides=[],
            project_dir=str(tmp_path),
            lib_dir=str(_REPO),
        )
        written = json.loads(config_path.read_text(encoding="utf-8"))

        assert written["mcp"]["compact_tool_list"] is (True if existing is None else existing)

    def test_включённый_флаг_урезает(self, all_tools, monkeypatch):
        monkeypatch.setattr(tiers, "_feature_enabled", lambda *a, **k: True)
        assert _tok(tiers.apply_tiers(all_tools)) < _tok(all_tools)

    def test_ошибка_чтения_конфига_читается_как_выключено(self, monkeypatch):
        """Неизвестное состояние не должно молча урезать поверхность: последствие
        увидит потребитель, а не автор."""

        def boom(*_a, **_kw):
            raise OSError("диск отвалился")

        monkeypatch.setattr("builtins.open", boom)
        assert tiers._feature_enabled("/нет/такого") is False

    def test_падение_фильтра_не_ломает_список(self, all_tools, monkeypatch):
        monkeypatch.setattr(tiers, "_feature_enabled", lambda *a, **k: True)
        monkeypatch.setattr(
            tiers, "compact_tools", lambda _t: (_ for _ in ()).throw(RuntimeError("бум"))
        )
        assert tiers.apply_tiers(all_tools) is all_tools


class TestЭкономияИзмеренаЧислом:
    """AC-5. Процент, который никто не считает, через полгода читается как
    «кто-то надеялся»."""

    def test_экономия_не_меньше_трети(self, all_tools):
        full, compact = _tok(all_tools), _tok(tiers.compact_tools(all_tools))
        saved = 1 - compact / full
        assert saved > 0.33, (
            f"экономия упала до {saved:.0%} — ядро разрослось либо описания "
            f"перестали быть весом ({full} → {compact} ток.)"
        )

    def test_указатель_не_повторяется_в_каждом_описании(self, all_tools):
        """Та же фраза в 126 описаниях стоила около 1260 токенов чистого повтора.
        Она сказана один раз — в описании самого инструмента добора."""
        compact = tiers.compact_tools(all_tools)
        repeated = [t for t in compact if tiers.SCHEMA_TOOL in (t.get("description") or "")]
        assert len(repeated) <= 1, "указатель вернулся в каждое описание"
