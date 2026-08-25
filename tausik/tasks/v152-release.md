---
slug: v152-release
title: "[P0] Release v1.5.2 — ship the public-readiness cleanup in a CLEAN tag"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "pyproject.toml, scripts/tausik_version.py, CHANGELOG.md, CHANGELOG.ru.md, docs/_generated/constants.json, README.md, README.ru.md, git tags + GitHub releases"
scope_exclude: "git HISTORY rewrite of main (commits) — still a separate maintainer call; no code logic changes"
relevant_files:
  - pyproject.toml
  - "scripts/tausik_version.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T01:30:33Z"
---

## Goal

The v1.5.1 tag/release predates the public-release-readiness cleanup, so its tarball STILL contains confidential docs/audit + the gitlab leak + broken docs. Cut v1.5.2 from the cleaned main so the LATEST public release is clean & complete (security purge, doc-accuracy, onboarding fixes, community health files). Bump 1.5.1→1.5.2, CHANGELOG [1.5.2], tag, GitHub release. Then retire the two defective superseded releases (v1.5.0 broken CLI; v1.5.1 confidential tarball) — delete their GitHub releases + tags so the public sees only the clean v1.5.2.

## Acceptance Criteria

AC1: pyproject + tausik_version = 1.5.2; gen_doc_constants --check green. AC2: CHANGELOG.md + .ru.md [1.5.2] — 2026-06-15 summarizing the public-readiness cleanup. AC3: full pytest green; ruff+mypy clean. AC4: tag v1.5.2 pushed + GitHub Release; the v1.5.2 tree contains NO docs/audit and NO gitlab leak (git ls-tree v1.5.2 clean). AC5: defective releases v1.5.0 + v1.5.1 deleted (GitHub releases + remote + local tags) so v1.5.2 is the only/latest release. Negative: `git ls-tree -r v1.5.2 | grep -E 'docs/audit|site/_archive'` is empty; README + quickstart links resolve.

## Plan

## Rollback

git revert the bump; tags re-creatable; deleted releases can be recreated from tags if needed.

## Journal

- 2026-06-15T01:30:02Z [implementation] — AC verified: 1. ✓ pyproject+tausik_version 1.5.2, gen_doc_constants --check green. 2. ✓ CHANGELOG.md+.ru.md [1.5.2] — 2026-06-15 (readiness cleanup). 3. ✓ full pytest 4213 passed/0 failed, ruff+mypy clean (210). 4. ✓ tag v1.5.2 pushed + GitHub Release (Latest); git ls-tree -r v1.5.2 | grep docs/audit|site/_archive = 0 (CLEAN tree). 5. ✓ defective v1.5.0 + v1.5.1 GitHub releases + remote/local tags DELETED (gh release delete --cleanup-tag); gh release list shows only v1.5.2; remote v1.5.x tags = only v1.5.2. Domain: a user installing 'latest' now gets a clean, working tree — no confidential audit material, no broken-CLI 1.5.0. Negative: v1.5.2 tree has zero docs/audit + site/_archive entries; only one release remains.
