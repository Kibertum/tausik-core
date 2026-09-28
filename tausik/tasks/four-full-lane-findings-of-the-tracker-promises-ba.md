---
slug: four-full-lane-findings-of-the-tracker-promises-ba
title: "Four full-lane findings of the tracker-promises batch: plan header, CLAUDE.md size cap, a matcher test, the logo test's scope"
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
  - TAUSIK-plan-1.9.md
  - CLAUDE.md
  - AGENTS.md
  - "tests/test_review_high_fixes.py"
  - "tests/test_readme_logo.py"
  - "tests/test_plan_19_names_the_composition_in_force.py"
  - "tests/test_claude_md_size.py"
scope_paths:
  - TAUSIK-plan-1.9.md
  - CLAUDE.md
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-13T17:32:24Z"
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

The full lane on the staged tree (session #259) is red on four tests the batch itself touched: TAUSIK-plan-1.9.md still names decision #369 while the map is built from #370; CLAUDE.md's static part grew to 4459 B over the 4096 B cap with the third memory row; tests/test_review_high_fixes.py expects task_call_counter on ONE entry while PR #5 registers a second MCP line; tests/test_readme_logo.py declares no CROSSCUTTING_SCOPE and imports no product module, so no change would ever select it. All four fixed at the root, the lane green on the staged tree.

## Acceptance Criteria

AC-1: tests/test_plan_19_names_the_composition_in_force.py passes — the plan's header names #370. AC-2: tests/test_claude_md_size.py passes with the three memory rows kept (the static part is trimmed, not the row dropped); measured before: 4459 B. AC-3: tests/test_review_high_fixes.py::TestHookMatcher::test_settings_matcher_excludes_read_only_tools passes by judging the union of task_call_counter's entries and still refusing Read/Grep/Glob on any of them (negative kept). AC-4: tests/test_crosscutting_registry.py passes — test_readme_logo.py declares CROSSCUTTING_SCOPE over the three pages and docs/assets/. AC-5 (negative): the full lane on the STAGED tree is green — 0 failed — before the commit; verify signed.

## Plan

## Rollback

## Journal

- 2026-09-13T17:32:21Z [implementation] — AC-1 ✓ TAUSIK-plan-1.9.md header names #370 (and the 13.09 note); tests/test_plan_19_names_the_composition_in_force.py passes. AC-2 ✓ CLAUDE.md static part 4459 B (measured before) → 4078 B with the three memory rows kept: the auto-memory bullet folded into its row, the rows shortened; tests/test_claude_md_size.py passes. AC-3 ✓ tests/test_review_high_fixes.py::TestHookMatcher::test_settings_matcher_excludes_read_only_tools judges the union of task_call_counter's entries and refuses Read/Grep/Glob on every entry (negative kept). AC-4 ✓ tests/test_readme_logo.py declares CROSSCUTTING_SCOPE (a literal list — the resolver reads it with ast.literal_eval) over the three pages and docs/assets/; tests/test_crosscutting_registry.py passes. AC-5 ✓ (NEGATIVE) full lane on the STAGED tree (git add -A before the run, memory #703): 10627 passed, 21 skipped, 0 failed, rc=0 (was 4 failed / 10623 passed). verify run #2637 signed. No changelog entry: the four fixes make the batch's own commit green. Domain: the lane judges what the commit will carry, and it is green.
