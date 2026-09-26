---
slug: whats-new-19-counts-its-entries-and-names-the-context-work
title: "What's new 1.9 counts its entries and names the context work"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "Two whats-new pages, one guard test, CHANGELOG line."
scope_exclude: "No new features; no change to which CHANGELOG entries are BREAKING; no release metadata."
relevant_files:
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
scope_paths:
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/whats-new-19-counts-its-entries-and-names-the-context-work.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T17:27:15Z"
resolution: null
resolution_reason: null
---

## Goal

docs/{ru,en}/whats-new-1.9.md says 'the Unreleased section holds 163 entries' while both CHANGELOGs hold 227 today — a number in a document that nothing counts rots silently (convention #673). The page also predates the effective-context and proof-integrity work that changes the UPDATE experience: the global user-tier config now scopes weakening per project (the 1.8 leak the owner flagged), task start prints a Relevant memory block, the regenerated CLAUDE.md carries a compaction section (preserve-if-exists!), knowledge export has --redacted, and caveman mode carries a response contract. The page must count its figure and name these.

## Acceptance Criteria

AC-1: the entry figure on both pages equals the live count of '### ' headings under [Unreleased] in the matching CHANGELOG, and tests/test_release_notes_1_9.py counts it — a stale figure fails. AC-2: both pages carry a section naming, in one paragraph each: project-scoped user-tier weakening (global config no longer applies another project's relaxations), the Relevant memory block on task start/show, the compaction contract in the regenerated rules file with the preserve-if-exists caveat, knowledge export --redacted, the response contract in caveman mode. AC-3 (negative): the page still holds far fewer items than the CHANGELOG and no more than the CHANGELOG marks — the existing guards stay green after the additions. AC-4: RU/EN paragraphs are parallel (translation-drift audit green); CHANGELOG EN/RU line; ruff; signed verify.

## Plan

## Rollback

git revert of the one commit.

## Journal

- 2026-09-12T17:27:05Z [implementation] — AC-1 ✓ tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_the_entry_figure_on_the_page_is_the_live_count[en|ru] — page states 228, CHANGELOGs hold 228 (was 163); negative proven by hand: EN page set back to 163 → 1 failed, restored. AC-2 ✓ section 'Контекст: между проектами, между сменами, через сжатие' / 'Context: across projects, across sessions, through compaction' — five paragraphs (project-scoped user tier, Relevant memory block, compaction section with the preserve-if-exists caveat, knowledge export --redacted, response contract). AC-3 ✓ ::test_it_carries_far_fewer_entries_than_the_changelog, ::test_it_holds_no_more_items_than_the_changelog_marks green after the additions. AC-4 ✓ tests/test_audit_translation_drift.py green (RU/EN parallel), CHANGELOG EN/RU lines, ruff clean, verify run #2537 signed. Root cause (documentation): a figure typed by hand and counted by nothing — the page said 163 while the log grew to 228; prevention: the page now names the test that counts it, and the test recounts on every run.
- 2026-09-26T19:02:59Z [done] — EVIDENCE-MOVED: tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_the_entry_figure_on_the_page_is_the_live_count[en|ru] => tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_the_entry_figure_on_the_page_is_the_live_count[en|ru]
- 2026-09-26T19:04:14Z [done] — EVIDENCE-MOVED: tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_the_entry_figure_on_the_page_is_the_live_count[en|ru] => tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_the_entry_figure_on_the_page_is_a_bound_the_changelog_clears
