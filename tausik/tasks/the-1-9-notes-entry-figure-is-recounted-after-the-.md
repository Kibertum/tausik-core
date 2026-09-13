---
slug: the-1-9-notes-entry-figure-is-recounted-after-the-
title: "The 1.9 notes' entry figure is recounted after the tag-refspec changelog entry"
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
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T14:47:43Z"
---

## Goal

docs/{en,ru}/whats-new-1.9.md state how many entries the Unreleased section holds; the changelog entry of task the-printed-release-acts-collide-with-the-dev-line raised the live count from 243 to 244 and the page still says 243 — tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_the_entry_figure_on_the_page_is_the_live_count fails on both languages.

## Acceptance Criteria

AC-1: both pages say 244 and test_the_entry_figure_on_the_page_is_the_live_count passes for en and ru. AC-2 (negative): the same test fails at 243 — measured before the edit (AssertionError: says 243 entries, the CHANGELOG holds 244), which is the reason the figure is counted by a test and not remembered. AC-3: gen_doc_constants --check stays OK; verify signed.

## Plan

## Rollback

## Journal

- 2026-09-13T14:46:56Z [implementation] — AC-2 (negative) measured BEFORE the edit: tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_the_entry_figure_on_the_page_is_the_live_count fails en+ru: 'whats-new-1.9.md says 243 entries, the CHANGELOG holds 244'.
- 2026-09-13T14:47:40Z [implementation] — AC-1 ✓ docs/en/whats-new-1.9.md and docs/ru/whats-new-1.9.md say 244; tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_the_entry_figure_on_the_page_is_the_live_count[en] and [ru] pass (217 passed with test_docs_links_resolve). AC-2 ✓ (NEGATIVE) the same test failed at 243 before the edit — logged above verbatim. AC-3 ✓ gen_doc_constants --check OK; verify run #2615 signed. Closed --no-changelog: a recount of a figure is a measurement, and a new entry would move the figure it recounts. Domain: the 1.9 notes count the Unreleased section, they do not remember it.
