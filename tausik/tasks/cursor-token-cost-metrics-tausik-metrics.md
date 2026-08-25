---
slug: cursor-token-cost-metrics-tausik-metrics
title: "Cursor: token/cost metrics в tausik metrics"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/**, agents/overrides/cursor/**, docs/**"
scope_exclude: "bootstrap/**, agents/overrides/qwen/**, agents/overrides/claude/**"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T16:06:47Z"
---

## Goal

Реализовать в TAUSIK фреймворке устойчивый сбор и отображение token/cost метрик для Cursor-сессий

## Acceptance Criteria

1) После завершения Cursor-сессии токены и cost записываются в проектные метрики автоматически. 2) tausik metrics показывает token/cost данные как минимум по последней сессии и агрегировано. 3) Отсутствие source-метрик не ломает команду и дает понятный warning. 4) Добавлены тесты/проверки на успешный и деградированный сценарии.

## Plan

## Rollback

## Journal

- 2026-04-28T15:06:00Z [implementation] — Реализовано: metrics record-session (CLI+service+backend), добавлена таблица session_usage_metrics (schema v19 + migration), вывод LLM Usage в tausik metrics, добавлены тесты tests/test_metrics_session_usage.py (2 passed).
- 2026-04-28T15:07:41Z [implementation] — Синхронизированы изменения и в source scripts, и в .claude/scripts (из-за wrapper). Команда '.tausik/tausik metrics record-session' работает, 'tausik metrics' показывает блок LLM Usage (tokens/cost/model). Тесты: tests/test_metrics_session_usage.py -> 2 passed.
- 2026-04-28T16:06:46Z [implementation] — Версионирование: scripts/tausik_version.py -> 1.4.0, добавлены CHANGELOG.md и CHANGELOG.ru.md записи 1.4.0.
- 2026-04-28T16:06:46Z [implementation] — Доведено до auto-режима: session_end запускает hooks/session_metrics.py --auto --record (best-effort), auto-detect транскриптов расширен на ~/.cursor/projects + ~/.claude/projects.
- 2026-04-28T16:06:47Z [implementation] — AC verified: 1. ✓ 2. ✓ 3. ✓ 4. ✓
- 2026-04-28T16:06:47Z [implementation] — Проверки: pytest tests/test_metrics_session_usage.py tests/test_session_end_metrics_hook.py (3 passed), smoke через python scripts/project.py metrics record-session + metrics (LLM Usage отображается).
