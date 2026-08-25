---
slug: mem-session-context-rule
title: "Усилить SessionStart-инжект — ⚠ правило в TAUSIK Memory Block"
status: done
epic: memory-discipline-hardening
story: memory-session-context-hardening
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_knowledge_aggregates.py, scripts/hooks/session_start.py"
scope_exclude: "Не трогать memory_compact, memory_add/list/delete. Не менять signature build_memory_block. Тесты — отдельная задача mem-session-context-test."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T22:46:39Z"
---

## Goal

Добавить в session_start hook (generator TAUSIK Memory Block) явное правило в самом верху блока: "⚠ TAUSIK memory = PRIMARY (это проект). Claude auto-memory = ONLY cross-project user preferences." Стабильный текст, который виден агенту с первого токена сессии.

## Acceptance Criteria

1. scripts/service_knowledge_aggregates.py::build_memory_block начинается со строки '⚠ Memory Policy: TAUSIK memory ... PRIMARY ... Claude auto-memory ... cross-project preferences only (marker: confirm: cross-project)'. Правило идёт сразу после заголовка '## TAUSIK Memory Block', до секций Decisions/Conventions/Dead ends. 2. scripts/hooks/session_start.py build_context Reminders секция получает новый bullet '- Claude auto-memory (~/.claude/*/memory/) is for cross-project user preferences only ...'. Идёт рядом с существующими reminder-ами. 3. Правило видно агенту в two places: (a) при наличии knowledge в БД — в Memory Block через session_start hook; (b) при пустой БД — через Reminders секцию session_start hook (fallback). 4. Существующие тесты test_memory_block.py::TestMemoryBlockContent::test_empty_db_returns_empty_string и остальные продолжают проходить без модификации. 5. Negative: правило НЕ появляется дважды если и memory_block и reminders оба отрисованы — reminders-версия формулируется короче и не дублирует wording буквально.

## Plan

## Rollback

## Journal

- 2026-04-22T22:43:58Z [implementation] — AC verified: (1) build_memory_block добавил в начале блока (строка 3 после заголовка+пустой строки) '⚠ Memory Policy — TAUSIK memory (tausik memory add) is the PRIMARY store ... Claude auto-memory (~/.claude/projects/*/memory/) is ONLY for cross-project user preferences ... marker confirm: cross-project' ✓. (2) session_start.py Reminders получил новый bullet '- Project knowledge → tausik memory add, NOT ~/.claude/*/memory/ (blocked by PreToolUse hook; bypass only with confirm: cross-project)' ✓. (3) Two-place injection: Memory Block (через build_memory_block) при наличии knowledge + Reminders (всегда) для empty-DB fallback ✓. (4) Регрессий нет: pytest tests/test_memory_block.py → 12 passed; pytest tests/test_session_start_hook.py → 8 passed. test_empty_db_returns_empty_string продолжает работать (guard 'if not decisions and not conventions and not deadends: return ""' сохранён) ✓. (5) Формулировки НЕ дублируются: memory_block версия с префиксом '⚠ **Memory Policy**' + развёрнутым объяснением; reminders версия компактная bullet — разные wording, нет буквального повтора ✓.
