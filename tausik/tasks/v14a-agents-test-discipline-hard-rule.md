---
slug: v14a-agents-test-discipline-hard-rule
title: "A2: AGENTS.md hard rule против тест-копий"
status: done
epic: v14-polish-critical
story: v14-polish-a-pre-push
complexity: null
role: tech-writer
stack: python
tier: trivial
call_budget: 5
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T10:17:53Z"
---

## Goal

Добавить в AGENTS.md hard rule: «не плодить тесты-копии — параметризуй или не пиши; не писать тесты на trivial getters». Ссылка на docs/en/testing-principles.md. Hard правило, чтобы фреймворк не плодил copy-paste тесты в новых проектах.

## Acceptance Criteria

1. AGENTS.md имеет новый hard rule «Не плодить тесты-копии» в секции Constraints или Test Discipline.
2. Rule явно сказан: parametrize или delete; не писать тесты на trivial getters; не дублировать тесты из других файлов.
3. Ссылка на docs/en/testing-principles.md.
4. Negative: остальные правила не тронуты.
5. Verify: grep "не плодить тесты\|copy-paste tests\|parametrize" AGENTS.md возвращает hit.
relevant_files: AGENTS.md

## Plan

## Rollback

## Journal

- 2026-05-03T10:17:53Z [implementation] — AC verified: 1. ✓ AGENTS.md «Testing discipline (agents) — HARD RULES» (header bold). 2. ✓ 7 явных rules: parametrize duplicates (3), no trivial getters (4), no mock-only (5), no implementation detail (6). 3. ✓ Ссылка на docs/{en,ru}/testing-principles.md. 4. ✓ Negative: остальные секции AGENTS не тронуты. 5. ✓ grep 'parametrize\|copy-paste\|trivial getters' AGENTS.md hits all keywords.
