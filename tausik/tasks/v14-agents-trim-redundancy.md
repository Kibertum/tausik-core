---
slug: v14-agents-trim-redundancy
title: "Редактура AGENTS.md: убрать дубли со skills без потери правил"
status: done
epic: v14-framework-lean
story: v14-lean-session-start
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: AGENTS.md
scope_exclude: null
relevant_files:
  - AGENTS.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T10:48:14Z"
---

## Goal

Меньше токенов при том же смысле.

## Acceptance Criteria

1. Diff с обоснованием. 2. Чеклист SENAR сохранён. 3. Negative: ни одно hard rule не удалено без замены ссылкой.

## Plan

## Rollback

## Journal

- 2026-05-01T10:48:13Z [implementation] — AC verified: 1. ✓ Осознанный diff (см. предыдущий log). 2. ✓ SENAR чеклист §The Rules сохранён. 3. ✓ Negative: каждое hard rule осталось или усилено ссылками без удаления императива task/verify/QG.
- 2026-05-01T10:48:13Z [implementation] — Diff justification: убраны дублирующие MCP/CLI/Skills блоки и ASCII work-cycle — заменены ссылками на docs + SKILL.md + явным verify перед closure. Чеклист SENAR (8 правил §The Rules) без изменений. Hard rules сохранены/усилены (verify-first упомянут в First 60). AC: документация как замена простыням.
