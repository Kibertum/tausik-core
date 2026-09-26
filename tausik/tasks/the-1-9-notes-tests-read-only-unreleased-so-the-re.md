---
slug: the-1-9-notes-tests-read-only-unreleased-so-the-re
title: "The 1.9 notes' tests read only [Unreleased], so the release-day cut of the CHANGELOG turns them red"
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
  - "tests/test_release_notes_1_9.py"
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T15:30:31Z"
resolution: null
resolution_reason: null
---

## Goal

tests/test_release_notes_1_9.py reads the entries of the '## [Unreleased]' section and the pages say 'the Unreleased section holds N entries'. The 1.8.0 cut (aa10f3b4) left '## [Unreleased]' with 'Nothing yet.' above '## [1.8.0] — date'; the same cut for 1.9 leaves that section EMPTY, so _unreleased() returns [], the entry-figure test fails (page says 245, section holds 0), 'shrank unexpectedly' fails (0 > 50), and the breaking-entries test checks nothing — on the release commit itself. The tests must read the 1.9 section: '## [1.9.0]' when it exists, '## [Unreleased]' before the cut; the page sentence must be true on both sides of the cut.

## Acceptance Criteria

AC-1: _section_for_1_9() returns the headings of '## [1.9.0]' when present, else of '## [Unreleased]'; unit test on a synthetic changelog for both shapes, and the post-cut shape ('[Unreleased]' with 'Nothing yet.' above '[1.9.0]') yields the 245 entries, not 0. AC-2 (negative): the same synthetic post-cut changelog read by the old Unreleased-only reader yields 0 — the failure the cut would have produced, shown in the test. AC-3: docs/{en,ru}/whats-new-1.9.md state the figure as the 1.9 section's ('the 1.9 section of the CHANGELOG holds N entries' / 'в разделе 1.9 CHANGELOG N записей'), the regex on the page follows, and the live count still matches (245). AC-4: tests/test_release_notes_1_9.py passes on the live tree; verify signed.

## Plan

## Rollback

## Journal

- 2026-09-13T15:30:28Z [implementation] — AC-1 ✓ tests/test_release_notes_1_9.py: _section_for_1_9 reads '## [1.9.0]' when present, else '## [Unreleased]'; ::TestTheReaderSurvivesTheReleaseCut::test_the_same_entries_are_read_on_both_sides_of_the_cut[before] and [after] — the post-cut shape ('[Unreleased]' + 'Nothing yet.' above '[1.9.0]') yields the two entries, not zero. AC-2 ✓ (NEGATIVE) ::test_the_old_unreleased_only_reader_would_have_read_zero_after_the_cut — _section(after, '## [Unreleased]') == [] is what the release commit would have produced under the old reader. AC-3 ✓ docs/en/whats-new-1.9.md 'the 1.9 section of the CHANGELOG holds 245 entries', docs/ru/whats-new-1.9.md 'в разделе 1.9 CHANGELOG 245 записей'; _ENTRY_FIGURE follows; live count matches (test_the_entry_figure_on_the_page_is_the_live_count en+ru pass). ::test_the_live_changelogs_are_on_one_side_of_the_cut_in_both_languages guards a half-cut. AC-4 ✓ 43 passed with tests/test_gate_test_dedupe.py (the two shape tests parametrised; ratchet 290/686 held); verify run #2623 signed. No changelog entry: a test-and-wording change that makes the release commit itself green. Domain: the notes' tests read the 1.9 SECTION, whichever heading it sits under on release day.
