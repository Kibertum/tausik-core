---
slug: v155-constants-readme-sync
title: "Sync constants + README test count after dogfood tests"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: simple
role: developer
stack: null
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T09:30:46Z"
---

## Goal

Dogfood fixes added 2 tests (4397→4399). Regen docs/_generated/constants.json and bump README badges so the doc-drift gate stays green for the v1.5.5 tag.

## Acceptance Criteria

1. constants.json test_count=4399. 2. README.md + README.ru.md badges read 4399. 3. gen_doc_constants --check PASSES. NEGATIVE: doc_drift_scanners stays clean (no other version/count mismatch introduced).

## Plan

## Rollback

git checkout README.md README.ru.md docs/_generated/constants.json

## Journal

- 2026-06-19T09:30:45Z [implementation] — AC1 ✓ constants.json test_count=4399. AC2 ✓ README.md + README.ru.md badges = 4399. AC3 ✓ gen_doc_constants --check PASSES (EXIT 0). NEGATIVE ✓ doc_drift_scanners clean (EXIT 0, no other mismatch).
