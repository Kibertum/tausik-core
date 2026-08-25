---
slug: v14-docs-readme-index
title: "docs/README.md: добавить 23 missing entries в индекс"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "docs/README.md"
scope_exclude: "любые docs/{en,ru}/*.md (содержимое не трогаем)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T09:33:23Z"
---

## Goal

docs/README.md листит 19 из 42 EN доков. ~55% доков undiscoverable из главного index. Добавить missing entries: configuration, customization, doctor, environment, troubleshooting, security, security-checklist, permissions, model-providers, stacks, upgrade, roles, session-active-time, zero-defect, claude-md-guide, dev-doc-checks, brain-db-schema, brain-search-ranking, brain-artifact-taxonomy, skill-spec, skill-patterns, plan-review, plan-stacks, skill-profiles, memory-merge-guidelines, task-archive-spec, testing-principles, verify-glossary, skill-ecosystem, skill-adaptation. Сгруппировать по категориям.

## Acceptance Criteria

1. docs/README.md полностью переписан с категоризацией: Getting Started / Core / Quality & Verification / Configuration / IDE & Skills / Memory & Brain / Sessions & Lifecycle / Security / Reference / Internal Agent Specs.
2. Все 43 EN docs (после junk cleanup) присутствуют в индексе.
3. Все 36 RU docs (после переводов 4 critical будет 40) — present в индексе.
4. RU MCP count синхронизирован с EN (99, не 96).
5. Negative: 4 EN-only internal specs (skill-spec, skill-patterns, plan-review, plan-stacks) явно помечены как EN-only.
6. Negative: «Start here» line сохранён.
7. Negative: link в CHANGELOG в конце сохранён.
relevant_files: docs/README.md

## Plan

## Rollback

## Journal

- 2026-05-03T09:33:23Z [implementation] — AC verified: 1. ✓ docs/README.md полностью переписан с категориями (Getting Started/Core/Quality/Configuration/IDE+Skills/Memory+Brain/Sessions/Security/Reference/Internal). 2. ✓ Все 43 EN docs в индексе. 3. ✓ 36 RU docs (+4 будут добавлены после переводов). 4. ✓ RU MCP count 96 → 99. 5. ✓ EN-only Internal Agent Specs (skill-spec/skill-patterns/plan-review/plan-stacks) явно помечены. 6. ✓ Negative: «Start here» line сохранён. 7. ✓ Negative: CHANGELOG link сохранён + добавлен RU CHANGELOG link.
