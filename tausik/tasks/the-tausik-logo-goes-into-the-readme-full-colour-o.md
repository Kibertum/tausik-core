---
slug: the-tausik-logo-goes-into-the-readme-full-colour-o
title: "The TAUSIK logo goes into the README: full-colour on the front pages, the monoline mark on the docs index"
status: done
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
  - "docs/README.md"
  - "docs/assets/README.md"
  - "docs/assets/tausik-logo.png"
  - "docs/assets/tausik-mark.png"
  - "tests/test_readme_logo.py"
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths:
  - README.md
  - README.ru.md
  - "docs/**"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-13T17:12:17Z"
---

## Goal

The owner delivered two renderings of the TAUSIK mark (a woman with a hairpin in a rounded frame): a monoline orange outline and a full-colour version. They live in the repository under docs/assets/ and appear where a reader meets the project: the full-colour logo at the top of README.md and README.ru.md, the monoline mark at the top of docs/README.md; every placement points at a file that exists.

## Acceptance Criteria

AC-1: docs/assets/tausik-logo.png (full-colour) and docs/assets/tausik-mark.png (monoline) exist, cropped to the frame with an even margin, PNG, black background as delivered. AC-2: README.md and README.ru.md show the full-colour logo above the title; docs/README.md shows the monoline mark; the images are referenced by repository-relative paths that render on GitHub and in the public snapshot. AC-3 (negative): tests/test_readme_logo.py resolves every image reference in the three files to a file on disk and fails on a missing one (a test on a made-up path is shown red). AC-4: the choice of which rendering goes where is written down in docs/assets/README.md with the reason; CHANGELOG EN/RU; verify signed.

## Plan

## Rollback

## Journal

- 2026-09-13T17:12:14Z [implementation] — AC-1 ✓ docs/assets/tausik-logo.png (956×956, full colour) and docs/assets/tausik-mark.png (895×895, monoline) — cropped to the frame with a 40 px margin on a square canvas, PNG, black ground as delivered (sources: the owner's 19:53 and 19:46 files of 2026-09-13; the 19:37 low-poly candidate is a different concept and is not used). AC-2 ✓ README.md and README.ru.md carry the colour logo above the title (width 200), docs/README.md the monoline mark (width 120); repository-relative paths; the snapshot dry-run publishes 1321 files, leaks 0/0. AC-3 ✓ tests/test_readme_logo.py::test_every_image_on_the_page_is_a_file[README.md|README.ru.md|docs/README.md], ::test_the_front_pages_carry_the_colour_and_the_docs_index_the_line; (NEGATIVE) ::test_a_made_up_asset_would_be_caught — the check is a file check. AC-4 ✓ docs/assets/README.md: which rendering goes where and why (first meeting = colour, repeat/small/one-colour = line; never both on one page); CHANGELOG EN/RU; whats-new figure 250; verify run #2635 signed. Domain: the mark meets the reader where the project is met first, and every picture on a front page is a file the tests can see.
