---
slug: v14-readme-new-features-coverage
title: "README EN+RU: добавить новые v1.4 фичи (artifact pipeline, multi-model, hygiene, audit, archive)"
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
completed_at: "2026-05-03T09:51:17Z"
---

## Goal

README.md и README.ru.md не упоминают 5 ключевых новых v1.4 фич: Brain Artifact Pipeline (propose→audit→publish), Multi-model Skill Profiles (variants/), Hygiene CLI (tausik hygiene archive), Audit Scripts (orphan/stale/unused/dedupe), Task Archive Spec. Это противоречит заявленному в CHANGELOG. Расширить Functionality таблицу + Advanced Features, добавить wow-effect.

## Acceptance Criteria

1. Functionality table расширена: Cross-project Brain row упоминает «artifact pipeline (propose → publish)», Skill Ecosystem row упоминает «multi-model profiles (variants/)».
2. Functionality table добавляет 2 новых row: «Hygiene & Audit» (audit_*.py + tausik hygiene archive) и «Task Archive» *(v1.4)*.
3. Advanced Features расширены 2 буллетами: Brain artifact pipeline (со ссылкой на docs/en/brain-artifact-taxonomy.md) и Audit suite (dev-doc-checks.md).
4. README.ru.md — зеркальные изменения.
5. Negative: остальные секции (Try It Now, How It Works, Supported IDEs, Dogfooding, Documentation) не тронуты.
6. Negative: первый экран (intro + 5 первых rows таблицы) сохраняет wow-effect.
relevant_files: README.md, README.ru.md

## Plan

## Rollback

## Journal

- 2026-05-03T09:51:17Z [implementation] — AC verified: 1. ✓ Functionality table: Cross-project Brain + Skill Ecosystem rows расширены (artifact pipeline + multi-model profiles). 2. ✓ +2 новых row: Hygiene & Audit, Task Archive. 3. ✓ Advanced Features +2 буллета: Brain artifact pipeline (links to taxonomy + ranking) + Audit suite (link to dev-doc-checks). 4. ✓ README.ru.md зеркальные изменения. 5. ✓ Negative: Try It Now/How It Works/Supported IDEs/Dogfooding/Documentation не тронуты. 6. ✓ Negative: первый экран (intro + Git аналогия + первые 5 rows) сохраняет wow-effect.
