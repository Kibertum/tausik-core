---
slug: prune-low-value-tests-by-behavioral-evidence
title: "Prune low value tests by behavioral evidence"
status: done
epic: null
story: null
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: "One evidence-ranked tranche of tests, obsolete fixtures/helpers, and release-lane repairs exposed by the mandated replay; research report and changelog."
scope_exclude: "No security-path weakening, no automatic deletion from AST similarity, no new count/existence governance tests, no paid model benchmark, no Kiberza, GitLab10, commit, push or release."
relevant_files:
  - "tests/test_release_notes_1_9.py"
  - "tests/test_publication_lines.py"
  - "tests/test_known_limitations.py"
  - "scripts/affected_test_selection.py"
  - "tests/test_affected_test_selection.py"
  - "docs/ru/research/release-111-test-pruning-evidence.md"
  - "changelog.d/evidence-based-test-pruning-111.md"
  - "tausik/gates.json"
scope_paths:
  - tests
  - scripts
  - "docs/ru/research"
  - changelog.d
  - pyproject.toml
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-10-02T10:12:56Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Remove or consolidate tests whose maintenance and execution cost exceeds demonstrated defect-detection value, without weakening security or core lifecycle guarantees.

## Acceptance Criteria

AC-1 Inventory classifies source-text, existence, exact-string, redundant meta and behavioral tests by cost and unique guarantee. AC-2 First bounded tranche removes or consolidates at least 10 percent of default test nodes or documents why a smaller evidence-backed boundary is safer. AC-3 Retained core behavior is supported by historical-defect, mutation or equivalent falsification evidence. AC-4 NEGATIVE: no replacement test merely checks the pruning machinery, counts or file existence. AC-5 Default and slow release lanes remain green with denominators, and changelog lists removed guarantees and preserved boundaries.

## Plan

[{"step": "Rank test families by runtime, maintenance coupling, source-text shape and unique behavioral guarantee", "done": true}, {"step": "Select a bounded low-value tranche and establish falsification evidence for preserved behavior", "done": true}, {"step": "Remove or parametrize candidates and simplify redundant repo-wide scans", "done": true}, {"step": "Run affected validation then one release cadence, report removed nodes/time/guarantees and close", "done": true}]

## Rollback

Restore the removed or consolidated tests and fixtures; revert selector/config/docs changes; rerun default and slow lanes to re-establish the prior guarantees.

## Journal

- 2026-10-01T22:58:04Z [planning] — Priority 4 after cheaper selection/output are available. First tranche targets low-value source/existence/exact-string and redundant meta scans; preserve security and core lifecycle behavior. Changelog is mandatory.
- 2026-10-02T09:58:09Z [implementation] — Step 1 done: reused the 8395-function inventory (53 document, 21 generated-freshness, 8321 behavior/review-needed), profiled four candidate families, and ranked repeated tracked-tree scans plus split editorial assertions as the first safe tranche.
- 2026-10-02T09:58:10Z [implementation] — Step 2 done: bounded tranche is release-notes 1.9, publication boundaries, and known-limitations entry points. Ten-percent global deletion is unsafe because the entire heuristic candidate pool is under 0.9% and the remaining 8321 tests lack behavioral classification. Historical defects and retained guarantees are mapped in docs/ru/research/release-111-test-pruning-evidence.md.
- 2026-10-02T09:58:10Z [implementation] — Step 3 done: consolidated 56 nodes to 35 (-21, 37.5% within tranche) without replacement governance/count tests. Publication leak assertions share one tracked-tree pass; focused tests pass 35/35.
- 2026-10-02T10:03:29Z [implementation] — Default lane found one honest ratchet failure: scripts/gate_command_runner.py was formatted by the preceding bounded-output task but remained in legacy_unformatted. Removed that stale baseline entry; no test guarantee changed. First full result: 12790 passed, 34 skipped, 143 deselected, 1 failed.
- 2026-10-02T10:09:03Z [implementation] — Slow lane exposed selector regression from the preceding affected-test task: explicit root-level test_calc.py was rejected when no tests/ root existed. Selector now treats an existing explicitly changed pytest file as an affected lane while malformed config or source-only projects still fail unavailable. Focused selector/runner tests: 34 passed; slow E2E will be replayed in the full slow lane.
- 2026-10-02T10:12:07Z [implementation] — AC-1/2: inventory classified 8395 functions and bounded removal to the 74 heuristic candidates; safe tranche consolidated tests/test_release_notes_1_9.py, tests/test_publication_lines.py and tests/test_known_limitations.py from 56 to 35 nodes (-37.5% tranche, ~0.16% default). AC-3: retained assertions still encode the historical 1.8 notes omission, publication leaks and onboarding-copy drift. AC-4 NEGATIVE: no test of pruning counts/machinery/file existence was added. AC-5: default 12791 passed/34 skipped/143 deselected; slow 143 passed/12826 deselected; exact evidence in docs/ru/research/release-111-test-pruning-evidence.md.
- 2026-10-02T10:12:07Z [implementation] — Release replay complete: scoped 69 passed; default 12791 passed, 34 skipped, 143 deselected; slow 143 passed, 12826 deselected. Two exposed regressions were repaired and re-run green.
- 2026-10-02T10:13:07Z [done] — AC-1: ✓ tests/test_release_notes_1_9.py, tests/test_publication_lines.py, tests/test_known_limitations.py classify and consolidate the selected families. AC-2: ✓ frozen inventory and 56→35 boundary documented in docs/ru/research/release-111-test-pruning-evidence.md. AC-3: ✓ historical defects remain executable in those three families. AC-4: ✓ no pruning/count test added; reviewed diff and audit. AC-5: ✓ default 12791/34/143 and slow 143/12826 are green. Domain: the real default and slow release commands completed successfully after exposing and repairing two live regressions.
