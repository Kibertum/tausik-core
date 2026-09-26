"""Полные схемы — только у ядра; остальные 126 выдаются по требованию.

ЗАМЕР, смена #275, по журналу .tausik/token_metrics.jsonl (единственный источник,
который пишет ИМЯ инструмента: в events `action='tool_use'` имени нет, `details`
пуст). 5782 вызова, из них с именем MCP — 75, то есть 1,3%; Bash — 4977, то есть
86%. Различных MCP-инструментов вызвано ШЕСТЬ из 147 объявленных.

СКОЛЬКО ЭТО СТОИТ — цифра уточнена и первая была завышена. Размер исходников
`tools*.py` даёт около 22 000 токенов, но там питоновский синтаксис и
комментарии; СЕРИАЛИЗОВАННЫЙ список, который уходит в запрос, — 14 317 токенов.
Меряется то, что посылается, а не то, что лежит на диске.

БАЗА ЗАМЕРА НАЗВАНА, а не умолчана: телеметрия ведётся с 07.09.2026, различных
смен в ней две. Вывод «шесть инструментов» опирается на два окна. Отношение
6 из 146 при 22 000 токенов статики не переворачивается ни при каком разумном
расширении базы, но список ядра ниже собран НЕ только по этим шести — иначе
первая же смена, позвавшая седьмой, заплатила бы лишним ходом.

ЧТО ИМЕННО УБИРАЕТСЯ. Не инструмент, а его СХЕМА. Имя и одна строка остаются в
списке, поэтому модель видит, что инструмент существует, и знает, где взять
описание. `call_tool` не тронут: скрытая схема не мешает вызову, а проверка
аргументов по-прежнему идёт по полному `TOOLS`. Это экономия контекста, а не
барьер, и путать их нельзя — ровно так же устроено `mcp_tool_scope`.

ПО УМОЛЧАНИЮ ВЫКЛЮЧЕНО. Источник правки прямо относит выгрузку инструментов к
тому, что ставится под флаг и проверяется замером, а не включается сразу: цена
ошибки — лишний ход на каждом разговоре, и она платится у потребителя, а не
здесь. Включается `mcp.compact_tool_list` в `.tausik/config.json`.

ЧЕГО ЗДЕСЬ НЕТ: просьбы к модели экономить. Меняется то, что посылает оснастка.
"""

from __future__ import annotations

import json
import os
from typing import Any

#: Ядро — полные схемы всегда. Собрано из трёх источников, и каждый назван:
#:
#:  * ЗАМЕРЕННЫЕ вызовы (шесть): task_log, memory_add, decide, session_handoff,
#:    session_end, session_start;
#:  * ПЕРВЫЙ ХОД — то, чем открывается смена и без чего агент не начнёт:
#:    session_open, status, task_list, task_next, task_show, update_claudemd;
#:  * ЖИЗНЕННЫЙ ЦИКЛ, на который опираются гейты: task_start, task_update,
#:    task_done, verify. Без них правило «нет кода без задачи» становится
#:    неисполнимым, и агент упирается в отказ, не имея чем его снять.
#:
#: Плюс поиск и знания — ими отвечают на вопрос «что тут уже известно», и
#: лишний ход за схемой здесь дороже самой схемы.
CORE_TOOLS: frozenset[str] = frozenset(
    {
        "tausik_session_open",
        "tausik_session_start",
        "tausik_session_end",
        "tausik_session_handoff",
        "tausik_status",
        "tausik_task_list",
        "tausik_task_next",
        "tausik_task_show",
        "tausik_task_start",
        "tausik_task_update",
        "tausik_task_done",
        "tausik_task_log",
        "tausik_verify",
        "tausik_search",
        "tausik_memory_add",
        "tausik_memory_search",
        "tausik_decide",
        "tausik_dead_end",
        "tausik_update_claudemd",
        "tausik_doctor",
        # Сам поиск схем — иначе выгруженное недостижимо.
        "tausik_tool_schema",
    }
)

#: Имя инструмента, которым добирают полную схему. Названо константой, потому
#: что оно попадает в текст указателя: строка «спроси где-нибудь» бесполезна.
SCHEMA_TOOL = "tausik_tool_schema"

#: Минимальная схема выгруженного инструмента. НЕ пустой объект: `additionalProperties`
#: разрешает аргументы, чтобы прямой вызов скрытого инструмента не отвергался
#: валидатором хоста до того, как дойдёт до нашего `call_tool`.
_STUB_SCHEMA: dict[str, Any] = {"type": "object", "additionalProperties": True}


#: Сколько символов описания остаётся у выгруженного инструмента. ВЫБРАНО
#: ЗАМЕРОМ, а не на вкус (смена #275), на живом списке из 147 инструментов:
#:
#:   первая строка целиком плюс указатель  10 444 ток.  −27%
#:   60 символов без указателя              8 582 ток.  −40%
#:   только имя                             6 920 ток.  −52%
#:
#: Взят средний. «Только имя» дешевле, но лишает модель признака, по которому
#: выбирают, ЧЕЙ схему просить, — и экономия уходит на лишний ход, что источник
#: правки называет прямо как ловушку. Шестидесяти символов хватает на «Create a
#: new epic…», то есть на выбор.
_KEEP_CHARS = 60


def _short(description: str) -> str:
    """Начало описания — ровно столько, чтобы выбрать инструмент.

    Указатель на `tausik_tool_schema` здесь НЕ дописывается, и это тоже замер:
    та же фраза в каждом из 126 описаний стоила около 1260 токенов чистого
    повтора. Она сказана ОДИН раз — в описании самого инструмента добора.
    """
    first = (description or "").strip().split("\n")[0]
    return first[:_KEEP_CHARS].rstrip()


def compact_tools(tools: list[dict]) -> list[dict]:
    """Список для `tools/list`: ядро целиком, остальные — имя и указатель.

    Порядок сохраняется. Он часть кэшируемого префикса, и перестановка
    инструментов между запросами обнуляет кэш так же надёжно, как правка текста.
    """
    out: list[dict] = []
    for tool in tools:
        name = tool.get("name", "")
        if name in CORE_TOOLS:
            out.append(tool)
            continue
        out.append(
            {
                "name": name,
                "description": _short(tool.get("description", "")),
                "inputSchema": dict(_STUB_SCHEMA),
            }
        )
    return out


def _feature_enabled(project_dir: str | None = None) -> bool:
    """`mcp.compact_tool_list` в `.tausik/config.json`. Выключено по умолчанию.

    Любая ошибка чтения — ВЫКЛЮЧЕНО. Неизвестное состояние конфига не должно
    молча урезать поверхность: последствие увидит потребитель, а не автор.
    """
    try:
        from project_config import find_tausik_dir

        base = project_dir or find_tausik_dir()
        with open(os.path.join(base, "config.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
        node = cfg.get("mcp")
        return bool(node.get("compact_tool_list")) if isinstance(node, dict) else False
    except Exception:  # noqa: BLE001 — неизвестность читается как «выключено»
        return False


def apply_tiers(tools: list[dict]) -> list[dict]:
    """Точка входа сервера. Fail-open: при любой ошибке отдаёт список как есть."""
    try:
        return compact_tools(tools) if _feature_enabled() else tools
    except Exception:  # noqa: BLE001 — урезание не смеет уронить tools/list
        return tools


def schema_reply(tools: list[dict], name: str | None, query: str | None) -> str:
    """Ответ `tausik_tool_schema`: полные схемы по имени либо по подстроке.

    Отказ НАЗЫВАЕТ, чем его снять. Инструмент существует ровно затем, чтобы
    выгруженная схема была достижима; «не найдено» без подсказки вернуло бы
    агента к угадыванию аргументов, то есть к тому, от чего выгрузка и спасает.
    """
    if name:
        for tool in tools:
            if tool.get("name") == name:
                return json.dumps(tool, ensure_ascii=False, indent=2)
        near = [t["name"] for t in tools if name.strip("_") in t.get("name", "")][:8]
        hint = f" Похожие: {', '.join(near)}." if near else ""
        return f"Инструмента '{name}' нет.{hint} Перечень: {SCHEMA_TOOL}(query='')."
    needle = (query or "").lower()
    found = [t for t in tools if needle in t.get("name", "").lower()]
    if not needle:
        return json.dumps([t["name"] for t in tools], ensure_ascii=False)
    if not found:
        return f"По '{query}' ничего. Перечень имён: {SCHEMA_TOOL}(query='')."
    if len(found) > 6:
        return json.dumps([t["name"] for t in found], ensure_ascii=False)
    return json.dumps(found, ensure_ascii=False, indent=2)
