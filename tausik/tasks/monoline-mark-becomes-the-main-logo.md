---
slug: monoline-mark-becomes-the-main-logo
title: "The monoline mark is the main logo; the full-colour rendering stays as tausik-logo-full"
status: done
epic: release-110-deferred-from-19
story: deferred-110-outward-loop-and-test-authorship
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/assets/README.md"
  - "docs/assets/tausik-logo.png"
  - "docs/assets/tausik-logo-full.png"
  - README.md
  - README.ru.md
  - "docs/README.md"
  - "tests/test_readme_logo.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "docs/assets/"
  - README.md
  - README.ru.md
  - "docs/README.md"
  - "tests/test_readme_logo.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-14T13:59:12Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Owner, session #264, with the monoline mark attached (the same one-stroke rendering already cropped into docs/assets/tausik-mark.png from the owner's 2026-09-13 original): it is the MAIN logo from now on; the full-colour rendering is kept as tausik-logo-full.png. Layout after: docs/assets/tausik-logo.png = the monoline (front pages README.md / README.ru.md and the docs index all show it), docs/assets/tausik-logo-full.png = the former full-colour file (kept, not placed), tausik-mark.png removed as a duplicate of the new logo. docs/assets/README.md restated, tests/test_readme_logo.py holds the new placement.

## Acceptance Criteria

AC-1: docs/assets/tausik-logo.png is byte-identical to the former tausik-mark.png; docs/assets/tausik-logo-full.png is byte-identical to the former tausik-logo.png; tausik-mark.png is gone. AC-2: README.md, README.ru.md and docs/README.md each show docs/assets/tausik-logo.png and nothing else (tests/test_readme_logo.py). AC-3: docs/assets/README.md names the two files and their roles truthfully. AC-4 (negative): a page pointing at an asset that does not exist is still caught — tests/test_readme_logo.py::test_a_made_up_asset_would_be_caught stays green.

## Plan

## Rollback

git revert; two renames and three img paths

## Journal

- 2026-09-14T13:58:59Z [implementation] — AC-1 ✓ git mv: tausik-mark.png → tausik-logo.png, tausik-logo.png → tausik-logo-full.png; cmp against HEAD blobs: both byte-identical. The attached Downloads file (photo_2026-09-14_16-55-04.jpg, Telegram-recompressed) is the uncropped source of the same monoline mark already cropped in the repo from the owner's 2026-09-13 original — the repo PNG is used, the JPG is not copied. AC-2 ✓ tests/test_readme_logo.py 5 passed: README.md, README.ru.md → docs/assets/tausik-logo.png; docs/README.md → assets/tausik-logo.png; -full exists. AC-3 ✓ docs/assets/README.md restated (monoline = the logo, colour = kept, not placed). AC-4 ✓ ::test_a_made_up_asset_would_be_caught green. CHANGELOG ×2 under the fresh [Unreleased].
