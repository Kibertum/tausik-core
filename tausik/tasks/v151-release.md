---
slug: v151-release
title: "[P0] Release v1.5.1 — critical CLI-clean-install fix (yaml lazy import)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "pyproject.toml, scripts/tausik_version.py, CHANGELOG.md, CHANGELOG.ru.md, docs/_generated/constants.json, README.md"
scope_exclude: "no code logic (fix already landed); no new features"
relevant_files:
  - pyproject.toml
  - "scripts/tausik_version.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T23:31:35Z"
---

## Goal

Cut v1.5.1 patch: ships the critical fix where v1.5.0's CLI crashed on a clean install (ModuleNotFoundError yaml). Bump version 1.5.0→1.5.1, add CHANGELOG [1.5.1] (EN+RU), sync version refs/badges, full test green, then tag v1.5.1 + push public + GitHub release. The fix itself landed in v151-fix-yaml-hard-import.

## Acceptance Criteria

AC1: pyproject + tausik_version = 1.5.1; gen_doc_constants --check green (no stale 1.5.0 refs). AC2: CHANGELOG.md + .ru.md have a [1.5.1] — 2026-06-15 section describing the yaml clean-install fix. AC3: full pytest green; ruff+mypy clean. AC4: tag v1.5.1 pushed to public github + GitHub Release created. Negative: a fresh-clone smoke of the 1.5.1 tree reaches a working `tausik status` without PyYAML in the env (the bug that triggered this patch).

## Plan

## Rollback

git revert the bump commit; a tag can be deleted before wide announce if a blocker surfaces.

## Journal

- 2026-06-14T23:31:11Z [implementation] — AC verified: 1. ✓ pyproject+tausik_version 1.5.1, gen_doc_constants --check green. 2. ✓ CHANGELOG.md+.ru.md [1.5.1] — 2026-06-15 (yaml clean-install fix). 3. ✓ full pytest 4205 passed/0 failed; ruff+mypy clean (210). 4. ✓ tag v1.5.1 pushed to public github + GitHub Release (releases/tag/v1.5.1). Negative: ✓ fresh-clone smoke of PUBLISHED v1.5.1 — clone → bootstrap --init → 'Project initialized and ready!' + `tausik status` works (the exact scenario that crashed 1.5.0). Domain: new users can now install + run 1.5.1 on a clean machine.
