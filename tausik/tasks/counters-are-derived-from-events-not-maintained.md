---
slug: counters-are-derived-from-events-not-maintained
title: "Счётчики ёмкости и чекпоинта ведутся рядом с журналом, хотя выводятся из него"
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
  - "scripts/checkpoint_signal.py"
  - "scripts/service_session.py"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "tests/test_checkpoint_counter_is_derived.py"
  - "tests/test_session_two_halves.py"
scope_paths:
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "scripts/service_session.py"
  - "scripts/checkpoint_signal.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - usage-attribution-is-keyed-by-task-not-session
completed_at: "2026-09-23T18:20:35Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#148"
started_model_id: claude-fable-5-1
started_model_version: null
done_model_id: claude-fable-5-1
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ПЕРЕНОС ФАКТОРА 5 (12-factor agents): объединить состояние ИСПОЛНЕНИЯ с состоянием предметной области и ВЫВОДИТЬ первое из журнала, а не вести рядом. Дословное предостережение фактора — не держать «сложные абстракции, отслеживающие то же самое отдельно».
У НАС ВЕДЁТСЯ ОТДЕЛЬНО: meta.tool_call_count (счётчик чекпоинта), счётчик ёмкости сессии (200 вызовов), активное время (180 мин). При этом usage_events уже несёт tool_calls, task_slug и recorded_at — то есть все три величины ВЫВОДИМЫ. Отдельное ведение уже давало рассинхрон: сохранение handoff обнуляло счётчик чекпоинта как побочный эффект (чинилось в 1.8, задача v2-session-split-and-drop).
ЧТО ДЕЛАЕТСЯ: счётчики становятся ЗАПРОСОМ к событиям, а не полем. Заодно снимается вопрос «что делать с гейтом ёмкости, когда сессия перестанет быть обязательной»: бюджет считается по активной ЗАДАЧЕ (call_budget уже есть и откалиброван, факт/бюджет 1.12 на n=10).
НЕГАТИВНОЕ: гейт, потерявший опору, обязан сказать это ВСЛУХ. Ровно этот дефект уже ловили — check_session_capacity возвращался рано при отсутствии сессии и переставал гейтить молча (fail-open). Повторить его при переносе будет вдвойне стыдно.
ЗАВИСИТ от атрибуции по задаче.

## Acceptance Criteria

1. Счётчик чекпоинта (SENAR 9.3) — запрос: вызовы текущей сессии из usage_events минус calls_at_write последнего handoff этой сессии; meta.tool_call_count больше не ведётся и не читается.
2. Ёмкость и активное время уже выводятся из журналов (session_capacity_summary по usage_events, active time по events) — подтверждено тестом, новых полей нет.
3. НЕГАТИВНЫЙ: без открытой сессии сигнал говорит вслух «сессии нет — вызовы не учитываются», а не молчит и не показывает ноль как измерение.
4. НЕГАТИВНЫЙ: запись handoff сбрасывает счёт через calls_at_write, а не побочным обнулением поля; предупреждение не повторяется на каждом вызове (одно на десяток вызовов сверх порога).
5. CHANGELOG EN+RU; docs.

## Plan

## Rollback

Замена полей на запросы; поля остаются в схеме до подтверждения. Откат — git revert.

## Journal

- 2026-09-23T18:09:00Z [implementation] — AC verified: 1 — счётчик чекпоинта — запрос usage_events сессии минус calls_at_write последнего handoff (tests/test_checkpoint_counter_is_derived.py::test_the_count_is_the_ledger_since_the_last_handoff; meta.tool_call_count не ведётся — assert None). 2 — ёмкость (session_capacity_summary по usage_events) и активное время (events) уже выводимы — новых полей нет. 3 — НЕГАТИВ ::test_without_a_session_it_says_so_aloud (no_session_note, None, не ноль). 4 — НЕГАТИВ ::test_advice_fires_once_per_ten_call_bucket; сброс — запись handoff (calls_at_write), test_session_two_halves переведён на checkpoint_warn_bucket. 5 — docs sessions.md, матрица ru/en; CHANGELOG EN+RU. meta_increment в бэкенде теперь без вызывающих — удаление оставлено уборке истории H (храповик class_surface требует опустить базу вместе с удалением). Verify #2707 зелёный.
- 2026-09-23T18:09:00Z [implementation] — verify #2707 green; tests/test_checkpoint_counter_is_derived.py incl. 2 negatives
- 2026-09-23T18:09:34Z [implementation] — verify #2707 green; tests/test_checkpoint_counter_is_derived.py incl. 2 negatives
- 2026-09-23T18:20:27Z [implementation] — verify #2714 green; tests/test_checkpoint_counter_is_derived.py incl. 2 negatives
