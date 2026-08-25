---
slug: v15p-escalating-nudges
title: "[P1] T2: Эскалирующие nudges silent→hint→warning→strong"
status: done
epic: v15-polish
story: v15p-agent-ux
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/nudge_escalation.py (новый: 4 уровня silent/hint/warning/strong, level_for_count, render_nudge, meta-backed bump/reset/peek per-invariant, resolve_thresholds из config). tests/test_nudge_escalation.py (новый)."
scope_exclude: "hooks/*.py (полная миграция существующих nudges — инкрементально позже, не в этой задаче), commit/task-done/push hard-блокировки (остаются жёсткими), service_session.py"
relevant_files:
  - "scripts/nudge_escalation.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T09:43:28Z"
---

## Goal

Заменить одношаговые напоминания (journaling, checkpoint, session limit) на эскалацию silent→hint→warning→strong (прецедент: barkain/claude-code-workflow-orchestration, отчёт T2). Жёсткие блокировки остаются только на commit/task done/push. AC: счётчик нарушений per-invariant в session state; 4 уровня эскалации с разными текстами; сброс при выполнении; конфиг порогов; тесты уровней.

## Acceptance Criteria

1. 4 уровня silent(0)→hint→warning→strong; level_for_count мапит счётчик→уровень по порогам; render_nudge даёт разный текст/префикс на уровень, пустую строку на silent. 2. Счётчик per-invariant в meta-таблице (bump инкрементит, peek читает, reset обнуляет при выполнении инварианта). 3. Пороги настраиваются через config (nudge.thresholds[invariant] override + дефолт). 4. Ошибка/boundary: неизвестный invariant / отсутствие meta-строки → счётчик 0 / silent, без исключения; битый config → дефолтные пороги. 5. pytest: уровни на границах + reset + config override + render тексты.

## Plan

## Rollback

git revert коммита; удалить nudge_escalation.py — фреймворк изолирован, ни один существующий вызов не зависит от него (greenfield), откат без побочных эффектов.

## Journal

- 2026-06-13T09:43:19Z [implementation] — nudge_escalation.py: 4 уровня SILENT/HINT/WARNING/STRONG, level_for_count по порогам, render_nudge (разные префиксы ⓘ/⚠/‼, '' на silent), meta-backed bump/peek/reset per-invariant (ключ nudge:<inv>), resolve_thresholds из config (override + дефолт), escalate() one-call. Все stateful — best-effort, never-raise. 22 теста зелёные. Регенерация test_count 3752->3774 + бейджи.
- 2026-06-13T09:43:26Z [implementation] — AC verified: 1. ✓ 4 уровня + render (TestLevelForCount, TestRenderNudge). 2. ✓ per-invariant счётчик в meta (TestCounterPersistence: bump/peek/reset, per-invariant изоляция). 3. ✓ config override (TestResolveThresholds: invariant+default block). 4. ✓ negative: malformed config->defaults, broken conn->silent (test_malformed_config_yields_defaults, test_broken_conn_never_raises). 5. ✓ pytest 22 passed.
