---
slug: journal-freshness-is-a-signal-not-a-rule
title: "Свежесть журнала — правило для агента, а не механизм: между записями теряется всё"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/journal_freshness.py"
  - "harness/claude/mcp/project/handlers.py"
  - "tests/test_journal_freshness.py"
scope_paths:
  - "scripts/checkpoint_signal.py"
  - "scripts/journal_freshness.py"
  - "harness/claude/mcp/project/handlers.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - qg0-does-not-refuse-work-for-session-time-or-capacity
completed_at: "2026-09-23T18:20:43Z"
resolution: null
resolution_reason: null
---

## Goal

ВЫВОД ANTHROPIC: компакция НЕОБРАТИМА, и ответ на это в масштабе — долговечный допрашиваемый ЖУРНАЛ, а не более умное сжатие. Наш журнал задачи append-only и едет в git — это ровно та конструкция. Но правило «непрерывное журналирование после каждого шага» записано как ПРАВИЛО ДЛЯ АГЕНТА в CLAUDE.md, а правила, которые агент обязан помнить, — ровно тот класс, который отказывает под давлением контекста.
СЛЕДСТВИЕ, НАБЛЮДАЕМОЕ У НАС: между записями журнала проходит по 20-40 вызовов; всё, что произошло между ними, живёт только в окне и умирает с ним. Проверить это утверждение замером по task_logs перед реализацией, а не принимать на веру.
ЧТО ДЕЛАЕТСЯ: свежесть журнала становится СИГНАЛОМ (N вызовов без записи по активной задаче — предупреждение, 2N — блокирующее для закрытия), по образцу существующего сигнала о просроченном чекпоинте. Данные для счёта уже есть: usage_events несёт tool_calls и task_slug.
НЕГАТИВНОЕ: сигнал не имеет права молчать при отсутствии открытой сессии — иначе он повторит дефект гейта ёмкости, который умел фейлиться открытым. Зависит от задачи об атрибуции по задаче, а не по сессии.

## Acceptance Criteria

1. ЗАМЕР ДО (смена #266, 80 последних закрытых задач, 218 промежутков между записями журнала, вызовы из usage_events по задаче): медиана 0, p90 2, ≥20 — 9, ≥40 — 3, максимум 209. Посылка «20–40 вызовов между записями» как типичное — опровергнута; хвост реален.
2. Сигнал: активная задача, у которой с последней записи task log прошло ≥ journal_freshness_calls (по умолчанию 40, основание — замер п.1: порог ловит хвост в 1,4% промежутков) вызовов, получает совет в ответе MCP; раз на десяток вызовов сверх порога.
3. НЕГАТИВНЫЙ: сигнал работает без открытой сессии (счёт по задаче, не по сессии) — не молчит.
4. НЕГАТИВНЫЙ: блокировки закрытия на 2N нет — гигиена есть сигнал (решение #376); основание записано в журнале задачи.
5. CHANGELOG EN+RU; docs.

## Plan

## Rollback

Новый сигнал в существующем механизме предупреждений. Откат — git revert; блокирующий порог за конфигом, отключается без правки кода.

## Journal

- 2026-09-23T17:51:55Z [implementation] — Замер записан в AC1. Отказ от блокировки закрытия на 2N: гигиена журнала — сигнал (решение #376); блокирующий порог обучал бы писать пустую строку журнала перед закрытием — ровно обход правила его же средствами.
- 2026-09-23T18:09:08Z [implementation] — AC verified: 1 — замер в AC1 (медиана 0, p90 2, ≥40 — 3 из 218). 2 — tests/test_journal_freshness.py::test_the_advice_fires_past_the_threshold_once_per_bucket, ::test_calls_after_the_last_log_are_counted; порог journal_freshness_calls (40), 0 выключает. 3 — НЕГАТИВ ::test_it_works_without_any_session. 4 — НЕГАТИВ ::test_it_never_refuses_a_closure; основание отказа от блокировки — в журнале. 5 — docs sessions.md ru/en, CHANGELOG EN+RU. Verify #2708 зелёный.
- 2026-09-23T18:09:09Z [implementation] — verify #2708 green; tests/test_journal_freshness.py 4 tests incl. 2 negatives
- 2026-09-23T18:09:42Z [implementation] — verify #2708 green; tests/test_journal_freshness.py 4 tests incl. 2 negatives
- 2026-09-23T18:20:35Z [implementation] — verify #2715 green; tests/test_journal_freshness.py incl. 2 negatives
