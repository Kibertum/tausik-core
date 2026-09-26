---
slug: version-ref-drift-exempts-dynamic-block-only-in-claudemd
title: "Version-ref drift check exempts the DYNAMIC block only in CLAUDE.md"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: developer
stack: python
tier: light
call_budget: 12
defect_of: null
scope: "One condition in the version-ref scanner; one test; CHANGELOG line."
scope_exclude: "No change to the foreign-prefix list or window; no change to what authored refs are scanned."
relevant_files:
  - "scripts/doc_drift_scanners.py"
  - "tests/test_doc_drift_scanners.py"
scope_paths:
  - "scripts/doc_drift_scanners.py"
  - "tests/test_doc_drift_scanners.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - "tausik/tasks/version-ref-drift-exempts-dynamic-block-only-in-claudemd.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T18:30:33Z"
resolution: null
resolution_reason: null
---

## Goal

Full lane after 3d91b228: test_check_docs_hook::TestRealRepoSync::test_exit_0_when_in_sync red on AGENTS.md:160 — decision #364's title 'RENAR re-assessment under corpus v1.1' in the generated memory tail read as a TAUSIK version claim. The version-ref scanner strips the generated DYNAMIC block for CLAUDE.md only (keyed on the filename), while AGENTS.md carries the same block as the sibling target; the 24-char foreign-prefix window did not reach 'RENAR'. The exemption must key on the marker, not on the file name.

## Acceptance Criteria

AC-1: the DYNAMIC block is stripped from every version-scan target that carries the markers, so a generated memory-tail title naming a foreign version in AGENTS.md is not a drift finding — test with a synthetic AGENTS.md. AC-2 (negative): an authored 'v1.1' in the static body of AGENTS.md is still a finding — test. AC-3: tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync green on the committed tree; full lane green. AC-4: CHANGELOG EN/RU line; ruff; signed verify.

## Plan

## Rollback

git revert of the one commit.

## Journal

- 2026-09-12T18:30:17Z [implementation] — AC-1 ✓ tests/test_doc_drift_scanners.py::TestTheDynamicBlockIsNotAnAuthoredVersionClaim::test_a_generated_title_in_agents_md_is_not_a_finding. AC-2 ✓ ::TestTheDynamicBlockIsNotAnAuthoredVersionClaim::test_an_authored_ref_in_the_static_body_is_still_a_finding (AGENTS.md:3 reported, the block below it silent). AC-3 ✓ tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync green on the tree with decision #364 in the tail; full lane run after commit. AC-4 ✓ CHANGELOG EN/RU, whats-new figure 229 → 230 by its guard, ruff clean, verify run #2541 signed. Root cause (logic-error): the DYNAMIC exemption was keyed on the file name CLAUDE.md while the generator writes the same block into the sibling AGENTS.md; a foreign product name 33 chars before the ref was outside the 24-char foreign window. Prevention: the strip keys on the markers for every target, and the negative test pins that authored refs are still scanned. Domain: a decision title may name any product's version; the rules file's generated tail is never an authored claim about TAUSIK.
