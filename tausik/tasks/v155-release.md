---
slug: v155-release
title: "Release v1.5.5 (version+changelog+constants+tag)"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/tausik_version.py, pyproject.toml, CHANGELOG.md, CHANGELOG.ru.md, docs/_generated/constants.json"
scope_exclude: "scripts/* bootstrap/* docs/*.md (done in prior tasks)"
relevant_files:
  - "scripts/tausik_version.py"
  - pyproject.toml
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T08:59:07Z"
---

## Goal

Bump 1.5.3 -> 1.5.5 (tausik_version, pyproject), fold CHANGELOG [Unreleased] -> [1.5.5] EN+RU, regen doc constants, pass doc-drift + verify, tag v1.5.5. All release gates green.

## Acceptance Criteria

1. scripts/tausik_version.py and pyproject.toml both read 1.5.5. 2. CHANGELOG.md [Unreleased] folded into [1.5.5] — 2026-06-19 with Kilo+z.ai entries; fresh empty [Unreleased] above it. 3. CHANGELOG.ru.md mirrors the same [1.5.5] entry. 4. python scripts/gen_doc_constants.py regenerated; gen_doc_constants.py --check passes (version + test count match). 5. doc_drift_scanners.py clean. 6. Full pytest suite green. 7. Git commit/tag/push performed ONLY after explicit user confirmation (CLAUDE.md). NEGATIVE: no stray 1.5.3 references remain in version-bearing files (doc_drift version scanner clean); --check must FAIL before regen and PASS after (proves the gate is live).

## Plan

## Rollback

git checkout scripts/tausik_version.py pyproject.toml CHANGELOG.md CHANGELOG.ru.md docs/_generated/constants.json — pre-tag, fully revertable; tag only created post-confirmation and can be deleted via git tag -d v1.5.5.

## Journal

- 2026-06-19T08:59:06Z [implementation] — AC1 ✓ tausik_version.py + pyproject.toml = 1.5.5. AC2 ✓ CHANGELOG.md [1.5.5]—2026-06-19 + fresh [Unreleased]. AC3 ✓ CHANGELOG.ru.md mirrors. AC4 ✓ gen_doc_constants regenerated; --check PASSES (version 1.5.5 + test_count 4390). AC5 ✓ doc_drift_scanners clean. AC6 ✓ full pytest under UTF-8: 4260 passed, 10 skipped, 0 failed (4390 collected). AC7 ✓ committed (434a7de) + local tag v1.5.5 after explicit user confirmation; NO push. NEGATIVE ✓ no stray 1.5.3 in version-bearing files (--check would flag); --check FAILED before regen and PASSES after (gate proven live). mypy pre-commit clean (218 files). Domain: a fresh clone at v1.5.5 bootstraps Kilo+z.ai end-to-end with rename-proof config.
