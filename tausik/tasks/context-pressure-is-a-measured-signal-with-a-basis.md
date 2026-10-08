---
slug: context-pressure-is-a-measured-signal-with-a-basis
title: "Давление контекста — измеренный сигнал с основанием, а не 180 минут и 200 вызовов из стандарта 2025 года"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/session_pressure.py"
  - "scripts/service_session_metrics.py"
  - "scripts/project_cli_ops.py"
  - "scripts/tausik_constants.py"
  - "scripts/checkpoint_signal.py"
  - "scripts/journal_freshness.py"
  - "harness/claude/mcp/project/handlers.py"
  - "tests/test_session_pressure.py"
scope_paths:
  - "scripts/tausik_constants.py"
  - "scripts/project_config.py"
  - "scripts/service_session_metrics.py"
  - "scripts/backend_session_metrics.py"
  - "scripts/session_pressure.py"
  - "scripts/status_view.py"
  - "scripts/hooks/session_cleanup_check.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_session.py"
  - "scripts/service_recording.py"
  - "scripts/checkpoint_signal.py"
  - "harness/claude/mcp/project/handlers.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - counters-are-derived-from-events-not-maintained
  - qg0-does-not-refuse-work-for-session-time-or-capacity
completed_at: "2026-09-23T18:20:52Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#174"
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

Числа 180 минут (tausik_constants: «SENAR v1.3: sessions exceeding 180 min show diminishing returns»), 150 минут предупреждения, 200 вызовов ёмкости и 40 вызовов до чекпоинта — самоустановленные пороги без записанного основания. SENAR 1.5 §9.4(c) требует основание и данные под ним для каждого числа, оставленного организации; §9.4(d) — эскалацию пересечения, а не тихий сдвиг; §10.2 говорит, что максимум ДОЛЖЕН опираться на эмпирические данные сессий. Наши данные есть: session recompute по сменам #196–#265 (70 смен) — медиана, p90, максимум активных минут; ни одна смена не достигла 180. Цель: три сигнала — активные минуты, вызовы с последнего чекпоинта, контекст (токены транскрипта из token metrics, где доступны) — с порогами, чьё основание СЧИТАЕТСЯ командой из живых данных (конвенция #673: число в документе обязано быть сосчитано), печатаются советом в status и Stop-хуке, а пересечение порога пишет событие эскалации. Ни один сигнал не отказывает.

## Acceptance Criteria

1. Команда (metrics sessions или расширение session recompute) печатает по окну последних N смен: медиану, p90, максимум активных минут, долю смен выше порога; документ docs/ru/session-active-time.md цитирует эти числа как вывод команды с датой, а тест проверяет, что документ содержит результат команды, а не устаревшее число (по образцу конвенции #673).
2. Пороги (session_max_minutes, session_warn_threshold_minutes, session_capacity_calls, checkpoint_calls) читаются из конфига с явной записью основания в docs/ru/session-active-time.md (§9.4(c)); константы в tausik_constants больше не ссылаются на «SENAR v1.3» как источник числа.
3. Пересечение порога пишет событие session_threshold_crossed с числом и порогом (§9.4(d)); повторные пересечения в одной сессии не спамят (одно событие на порог на сессию).
4. НЕГАТИВНЫЙ: ни один сигнал не превращается в отказ tool call, task start или task done — тест прогоняет все три сценария с пороговыми значениями.
5. НЕГАТИВНЫЙ: порог 0 или отсутствующий ключ = сигнал выключен, ничего не печатается и не пишется; тест.
6. Сигнал «свежесть журнала» (минуты с последней записи task log активной задачи) входит в тот же набор советов (см. journal-freshness-is-a-signal-not-a-rule) — без отказа.
7. CHANGELOG EN+RU; docs/ru+en.

## Plan

## Rollback

git revert; конфиг-ключи обратно совместимы (старые имена читаются).

## Journal

- 2026-09-23T18:20:43Z [implementation] — AC verified: 1 — session recompute печатает SUMMARY (median/p90/max/above threshold); docs session-active-time ru/en цитируют вывод с датой (медиана 73, p90 146, выше 180 — 1 из 70); tests/test_session_pressure.py::test_summary_gives_the_basis_figures. 2 — пороги из конфига с основанием в docs; tausik_constants больше не ссылается на SENAR v1.3 как источник числа. 3 — ::test_a_crossing_is_recorded_once (session_threshold_crossed раз на сессию). 4 — НЕГАТИВ ::test_no_signal_ever_refuses_a_start. 5 — НЕГАТИВ ::test_a_zero_threshold_switches_the_signal_off; checkpoint_calls и journal_freshness_calls = 0 выключают. 6 — свежесть журнала — отдельная закрытая задача. 7 — CHANGELOG EN+RU, docs. Verify #2716 зелёный. Попутно найдена и исправлена ошибка собственного замера (1 из 70 смен пересекла 180) — память #727, решение #381.
- 2026-09-23T18:20:44Z [implementation] — verify #2716 green; tests/test_session_pressure.py incl. 2 negatives
