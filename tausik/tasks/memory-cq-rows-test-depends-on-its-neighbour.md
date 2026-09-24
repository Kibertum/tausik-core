---
slug: memory-cq-rows-test-depends-on-its-neighbour
title: "test_memory_cq_rows: второй тест рендерера импортирует handlers_knowledge через путь, который вставляет первый — под xdist они попадают в разные воркеры и второй падает ModuleNotFoundError"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_memory_cq_rows.py"
scope_paths:
  - "tests/test_memory_cq_rows.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:39:50Z"
---

## Goal

Тест test_mcp_formatter_keeps_address_for_local проходит сам по себе и в любом порядке: путь к harness/claude/mcp/project вставляется на уровне модуля, а не внутри соседнего теста.

## Acceptance Criteria

1. tests/test_memory_cq_rows.py::TestRenderersTolerateMissingAddress::test_mcp_formatter_keeps_address_for_local проходит запущенный ОДИН (до правки — ModuleNotFoundError: handlers_knowledge).
2. НЕГАТИВНЫЙ: оба теста класса проходят в обратном порядке (-p no:randomly не нужен: каждый самодостаточен).

## Plan

## Rollback

git revert одной правки теста

## Journal

- 2026-09-23T19:36:40Z [implementation] — Причина: sys.path к harness/claude/mcp/project вставлял первый тест класса; второй полагался на это. Под xdist (verify негативного знания, 23.09) они попали в разные воркеры — ModuleNotFoundError: handlers_knowledge. Правка: вставка пути на уровне модуля. Воспроизведение до правки — в verify задачи negative-knowledge-is-voluntary-and-therefore-absent.
- 2026-09-23T19:36:41Z [implementation] — AC-1: ✓ tests/test_memory_cq_rows.py::TestRenderersTolerateMissingAddress::test_mcp_formatter_keeps_address_for_local
- 2026-09-23T19:36:41Z [implementation] — AC-2: ✓ tests/test_memory_cq_rows.py::TestRenderersTolerateMissingAddress::test_mcp_formatter_omits_address_for_cq
- 2026-09-23T19:36:41Z [implementation] — NO-DEAD-END: причина найдена с первого взгляда, альтернативных подходов не пробовалось
