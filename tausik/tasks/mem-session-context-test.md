---
slug: mem-session-context-test
title: "Тест: injected-context содержит новое правило"
status: done
epic: memory-discipline-hardening
story: memory-session-context-hardening
complexity: simple
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_memory_block.py, tests/test_session_start_hook.py"
scope_exclude: "Не трогать scripts/service_knowledge_aggregates.py или session_start.py. Не рефакторить существующие тесты."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T22:50:32Z"
---

## Goal

Pytest: session_start hook output содержит ⚠-правило в ожидаемой позиции и ожидаемым текстом. Регресс-тест на случай рефакторинга memory_block_generator.

## Acceptance Criteria

1. tests/test_memory_block.py::TestMemoryBlockContent получает новый тест test_memory_policy_rule_at_top_of_block — проверяет что build_memory_block при наличии знания начинается с '## TAUSIK Memory Block' и затем первая непустая строка после заголовка содержит '⚠' и фразу 'confirm: cross-project'. 2. tests/test_session_start_hook.py получает новый тест class TestMemoryPolicyReminder::test_reminder_includes_auto_memory_policy — проверяет что build_context() output содержит reminder bullet '- Project knowledge → tausik memory add' ИЛИ '~/.claude/*/memory/' ИЛИ 'confirm: cross-project'. Тест использует существующие fixtures/моки session_start test file. 3. NEGATIVE: тест test_policy_rule_ordering_before_decisions — правило идёт ДО первой строки 'Recent decisions'. Если кто-то refactor-ит build_memory_block и поставит правило ПОСЛЕ decisions — тест упадёт. 4. Все новые тесты проходят локально. Существующая 1130-тестовая сьюта продолжает работать без регрессий.

## Plan

## Rollback

## Journal

- 2026-04-22T22:47:57Z [implementation] — AC verified: (1) TestMemoryBlockContent::test_memory_policy_rule_at_top_of_block — первая непустая строка после '## TAUSIK Memory Block' содержит ⚠ + 'confirm: cross-project' + 'tausik memory add' ✓. (2) TestMemoryPolicyReminder::test_reminder_includes_auto_memory_policy — session_start hook ctx содержит 'Project knowledge' + 'tausik memory add' + '~/.claude/*/memory/' + 'confirm: cross-project' ✓. (3) NEGATIVE test_policy_rule_ordering_before_decisions: rule_idx < decisions_idx ✓. (4) NEGATIVE test_policy_reminder_sits_with_other_reminders: reminders_idx < policy_idx ✓. (5) Все тесты проходят: test_memory_block.py → 14 passed (+2 new), test_session_start_hook.py → 10 passed (+2 new). Регрессий нет.
