---
slug: v14-changelog-epics-split
title: "CHANGELOG: split 5 bundled v14-* эпиков на раздельные секции"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T09:34:40Z"
---

## Goal

CHANGELOG.md и .ru.md имеют '### Added — Hygiene & audit tooling' секцию которая bundles 5 эпиков (v14-project-hygiene, v14-test-philosophy, v14-doc-automation, v14-dead-code-audit, v14-skill-store). Раскрыть в 5 параллельных '### Added — Epic v14-{slug}' секций для согласованности с первыми 5 эпиками.

## Acceptance Criteria

1. CHANGELOG.md секция «### Added — Hygiene & audit tooling» split на 5 секций по эпикам: project-hygiene (hygiene archive CLI), test-philosophy (audit_pytest_dedupe), dead-code-audit (audit_orphan_files + audit_stale_docs + audit_unused_python), doc-automation (check_docs hook + .github workflow + dev-doc-checks docs), skill-store (skill CLI consistency).
2. CHANGELOG.ru.md тот же split в зеркальной форме.
3. Введение «All 10 v14-* epics closed in this release» сохраняется как summary параграф над разбивкой.
4. Negative: контент пунктов не теряется — каждый bullet перенесён в правильную секцию.
5. Negative: «Refactored» секция (project_parser.py extraction) после splits сохраняется.
relevant_files: CHANGELOG.md, CHANGELOG.ru.md

## Plan

## Rollback

## Journal

- 2026-05-03T09:34:40Z [implementation] — AC verified: 1. ✓ CHANGELOG.md split на 5 секций по эпикам с заголовками '### Added — Epic v14-{slug} ({description})'. 2. ✓ CHANGELOG.ru.md зеркальный split. 3. ✓ Введение 'All 10 v14-* epics closed' сохранено как summary параграф над разбивкой. 4. ✓ Все bullets перенесены без потерь по правильным эпикам. 5. ✓ Refactored секция (project_parser.py) сохранена ниже splits.
