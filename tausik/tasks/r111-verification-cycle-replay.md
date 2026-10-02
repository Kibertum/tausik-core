---
slug: r111-verification-cycle-replay
title: "Replay a real verification cycle without a second model return"
status: active
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "Offline replay evidence for one actual release-111 adjacent verification pair; deterministic equivalence/refusal evaluator, fixture, tests and changelog only."
scope_exclude: "No change to verification execution, compound close semantics, model routing, release metadata, commit, push or release."
relevant_files:
  - "scripts/verification_cycle_replay.py"
  - "tests/test_verification_cycle_replay.py"
  - "tests/fixtures/verification_cycle_replay.json"
  - "changelog.d/verification-cycle-replay-111.md"
scope_paths:
  - "scripts/verification_cycle_replay.py"
  - "tests/test_verification_cycle_replay.py"
  - "tests/fixtures/verification_cycle_replay.json"
  - "changelog.d/verification-cycle-replay-111.md"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Prove one chosen deterministic verification cycle preserves verdict, counts and failure evidence while replacing an adjacent independent verification return with compound task done --verify.

## Acceptance Criteria

AC-1 A frozen replay identifies an actual adjacent verification pair from release-111 topology evidence and rejects adaptive or dependent pairs. AC-2 The before/after replay has identical relevant verdict, counts and failure evidence, with explicit model-return boundaries. AC-3 Negative: if no independently removable pair exists, the replay refuses to claim a reduction. AC-4 Scoped tests and recorded evidence show the chosen cycle is deterministic and offline.

## Plan

[{"step": "Freeze the actual adjacent pair and its artifact provenance", "done": true}, {"step": "Implement deterministic equivalence and refusal evaluation", "done": true}, {"step": "Test equivalent, adaptive, dependent and evidence-loss branches offline", "done": true}, {"step": "Record the truthful replay verdict without claiming an unsupported reduction", "done": true}]

## Rollback

Remove the replay evaluator, fixture, tests and changelog fragment; verification runtime remains unchanged.

## Journal

- 2026-10-01T22:10:59Z [implementation] — Started: select an actual deterministic adjacent verification pair from frozen release-111 topology evidence; no implementation path will be altered by this evidence task.
- 2026-10-01T22:15:20Z [implementation] — Dead end: the frozen topology names only aggregate body-free transitions and the retained native corpus yields zero accepted verification-to-verification windows. It cannot identify a real pair or compare verdict/count/failure payloads, so AC-1/AC-2 cannot be honestly proven from retained evidence; fixture records an explicit refusal.
- 2026-10-01T22:15:20Z [implementation] — Implemented deterministic offline refusal fixture/test. It preserves the aggregate 111 observation and rejects aggregate-only, adaptive/dependent, and missing-equivalence claims rather than converting them into savings.
- 2026-10-01T22:21:31Z [implementation] — Investigation: default CODEX_HOME scan (270 session files; accepted slugs via usage_codex_report._accepted_tasks) found a real adjacent pair in r111-compact-verification-output native rounds 18→19. Round 18 ran scoped pytest/ruff/diff (80 passed); round 19 ran canonical task verify and refused red (#3315: ruff_format/bootstrap_drift; pytest skipped). The frozen topology classifier also overcounts patch text containing pytest, so its aggregate cannot select this pair alone.
- 2026-10-01T22:21:32Z [implementation] — AC-2 remains unmet: task done --verify runs only canonical run_verify_for_task. It preserves the second refusal but does not execute or retain the preflight 80-pass count and git diff evidence. A truthful composition needs a declared reusable preflight-check bundle executed within the close transaction, with both subresults persisted in the same durable report; then an offline replay can compare the two-result sequence against that single response. This task owns evidence only and makes no implementation change.
- 2026-10-01T22:37:18Z [implementation] — Correction to logs #4646/#4649: the provisional negative fixture/test/changelog were removed, so no replay implementation remains. Root and Sol review rejected a generic preflight command bundle as duplicated verification and scope expansion. Exact natural-pair replay remains unproven because canonical verify does not preserve the separate preflight outputs. A future valid proof needs retained natural pair plus frozen repository/config/output, or a justified equivalence proof covering every original result. Gate-batching capability alone is not accepted as this replay. AC2 remains explicitly unmet.
- 2026-10-02T10:16:37Z [implementation] — Frozen actual r111-compact-verification-output rounds 18→19 with topology snapshot hash, 80-pass preflight observation and canonical red verify #3315 artifact hash.
- 2026-10-02T10:16:38Z [implementation] — 10 offline tests pass for actual refusal, exact equivalence, adaptive/dependent pairs, every observable field and adjacency/topology negatives.
- 2026-10-02T10:16:38Z [implementation] — Actual replay refuses the reduction: compound close omits the preflight observation. AC-2 remains unmet by design; no token or boundary saving is claimed.
- 2026-10-02T10:16:38Z [implementation] — Implemented strict offline evaluator: only adjacent independent verification pairs qualify, and verdict/count/failure/evidence observations must match exactly.
- 2026-10-02T10:17:00Z [implementation] — AC-1: ✓ frozen fixture names actual rounds 18→19 and topology 111 occurrences; adaptive/dependent/non-adjacent candidates are rejected. AC-2: ✗ actual before/after are not identical because compound omits the 80-pass preflight result. AC-3: ✓ evaluator refuses claim_reduction. AC-4: ✓ 10 deterministic offline tests and verify #3355 pass. Domain: canonical verify #3315 artifact hash matches the frozen failure evidence. Per owner instruction the task remains active and unmet; handle #3355 is not consumed.
