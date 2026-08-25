---
slug: hotfix-skip-test-skill-bundles-when-skills-officia
title: "Hotfix: skip test_skill_bundles when skills-official not vendored"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_skill_bundles.py"
scope_exclude: "scripts/skill_bundles.py, skills-official/, .github/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T21:12:15Z"
---

## Goal

test_skill_bundles.py reads skills-official/bundles.json + skills-official/registry.json. skills-official/ is in .gitignore (separate repo Kibertum/tausik-skills) so CI clones tausik-core without it; 7 tests fail with BundleError "No bundles manifest" / FileNotFoundError "registry.json". Pre-existing baseline drift: tests added in v14b-skill-bundles-marketplace never ran on CI. Add module-level pytest.skip when bundles.json is absent so the file becomes a no-op in environments without the vendored skills repo, keeping local coverage intact.

## Acceptance Criteria

AC-1: tests/test_skill_bundles.py — add module-level pytest.skip(..., allow_module_level=True) when skills-official/bundles.json is absent (skip reason references the .gitignore design and points at docs/en/skill-bundles.md); AC-2 (negative): when skills-official/bundles.json IS present (local dev), all 14+ tests still run unchanged — verified by running scoped pytest locally with skills-official/ present; AC-3: GitHub CI (Kibertum/tausik-core) goes green on next push (no fails on Linux/macOS/Windows × 3.11/3.12/3.13).

## Plan

## Rollback

## Journal

- 2026-05-07T21:12:08Z [implementation] — Module-level pytest.skip added at the top of tests/test_skill_bundles.py: when os.path.isfile(BUNDLES_PATH) is False, raise pytest.skip(... allow_module_level=True) with reason citing .gitignore design + pointer to docs/en/skill-bundles.md. AC-1: ✓ skip block present. AC-2: ✓ local dev (skills-official/bundles.json present) — 22 tests still PASS, ruff green. AC-3: pending CI push verification.
