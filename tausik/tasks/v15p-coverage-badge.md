---
slug: v15p-coverage-badge
title: "[P2] Coverage % через pytest-cov + badge"
status: done
epic: v15-polish
story: v15p-debt
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "README.md (badge + baseline note), .github/workflows/test-coverage.yml (artifact upload), .gitignore (coverage.json), docs note, tests/test_coverage_badge.py"
scope_exclude: "no external service (Codecov); no dynamic endpoint; pyproject [tool.coverage] already configured — unchanged"
relevant_files:
  - README.md
  - ".github/workflows/test-coverage.yml"
  - ".gitignore"
  - "tests/test_coverage_badge.py"
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T18:24:56Z"
---

## Goal

Техдолг #7: «3400 tests passing» не отражает покрытие. Включить pytest-cov в CI, публиковать % (badge в README), зафиксировать baseline. AC: coverage отчёт в CI артефактах; badge живой; baseline задокументирован.

## Acceptance Criteria

AC1: CI (test-coverage.yml) uploads the coverage report (coverage.json) as a build artifact. AC2: a static shields.io coverage badge is in README reflecting the measured baseline (76%). AC3: the baseline is documented (value + test count + how to refresh) in a tracked doc. AC4: coverage.json build artifact is gitignored (not committed). AC5: a regression test asserts the README coverage badge exists and the workflow uploads the artifact; ruff/filesize clean. Negative: if coverage.json is absent, the CI artifact-upload step does not fail the run (if-no-files-found: ignore) and the regression test still passes (it asserts presence of the badge/step, not a live %).

## Plan

## Rollback

git revert; additive badge + CI step + doc, no runtime code touched.

## Journal

- 2026-06-14T18:24:42Z [implementation] — Measured baseline: 76.17% line coverage (12848/16867 stmts in scripts/, 4124 selected tests). Approach C (static shields.io, per user choice — consistent with repo 0-deps ethos). README: coverage-76% badge + baseline note (value + refresh cmd). test-coverage.yml: added upload-artifact step (coverage-report/coverage.json, if-no-files-found: ignore — negative path). .gitignore: coverage.json. 4 regression tests (badge present, baseline documented, CI uploads artifact incl if-no-files-found, gitignored). No external service.
- 2026-06-14T18:24:56Z [implementation] — AC1: ✓ test-coverage.yml uploads coverage.json as 'coverage-report' artifact (upload-artifact@v4) — test_ci_uploads_coverage_artifact. AC2: ✓ static shields.io coverage-76% badge in README — test_readme_has_coverage_badge. AC3: ✓ baseline documented in README Proof section (76% line coverage, scripts/, 4124 tests + refresh command) — test_baseline_documented. AC4: ✓ coverage.json gitignored — test_coverage_json_gitignored (root artifact deleted). AC5: ✓ 4 regression tests; ruff clean; YAML valid. Negative: upload step uses if-no-files-found: ignore so an absent coverage.json doesn't fail CI; test asserts presence of badge/step not a live % — stable when coverage.json absent. Domain: 76% measured from a real full run (4124 passed, 8 skipped, 309s); badge reflects actual scripts/ line coverage.
