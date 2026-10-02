---
slug: r111-round-topology
title: "Map accepted-task round topology and choose three eliminable cycles"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/round_topology.py"
  - "tests/test_round_topology.py"
  - "docs/ru/research/release111-round-topology.md"
  - "changelog.d/round-topology-111.md"
scope_paths:
  - "scripts/round_topology.py"
  - "tests/test_round_topology.py"
  - "docs/ru/research/release111-round-topology.md"
  - "changelog.d/round-topology-111.md"
scope_tools: []
depends_on: []
completed_at: "2026-10-01T20:34:44Z"
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

Use existing native Codex traces to identify and rank deterministic workflow sequences that cause avoidable model returns, then freeze the three highest-value implementation targets.

## Acceptance Criteria

AC-1 An offline artifact reports the exact transcript, accepted-window and response-round denominators. AC-2 The three highest-value removable sequences each name the before sequence, proposed compound replacement, occurrence count and upper-bound rounds removed. AC-3 Every result is reproducible without a model call or network request. AC-4 Negative: unattributed or ambiguous responses remain excluded and the report makes no causal token-savings claim.

## Plan

[{"step": "Extract ordered action and response transitions from existing accepted Codex windows", "done": true}, {"step": "Rank repeated deterministic turnback sequences by removable outer rounds", "done": true}, {"step": "Freeze three targets with denominators, boundaries and implementation handoffs", "done": true}, {"step": "Verify the analyzer and publish the evidence artifact", "done": true}]

## Rollback

Remove the new offline analysis artifact and analyzer changes; no runtime behavior changes in this task.

## Journal

- 2026-10-01T20:29:37Z [planning] — USER SPEC: continue 1.11 rather than release; maximize expense reduction by attacking model rounds and repeated prefix; use existing real traces; no synthetic paid benchmark fan-out; keep GLM theoretical per Decision 414; do not commit, push, release or change GitLab 10 without separate permission. Baseline is 1036 responses over 18 accepted tasks (57.6 rounds/task), with 97.6 percent cached project input.
- 2026-10-01T20:33:39Z [implementation] — Measured 43 real project transcripts, 18 successful DB-accepted windows, 1566 response rounds and 19 excluded ambiguous boundaries. Frozen targets: retrieval-to-retrieval 116, verification-to-verification 111, verification-to-task-progress 40. Counts are upper bounds, categories are not added across overlap, and no token saving is claimed. Analyzer persists no transcript body. Focused tests and mypy are green.
- 2026-10-01T20:34:13Z [implementation] — Typecheck correction: renamed the pending three-field boundary variable so mypy no longer conflates it with the two-field action boundary. No behavioral change.
- 2026-10-01T20:34:39Z [implementation] — AC-1: ✓ round-topology-20261001.json reports 43 transcripts, 18 accepted windows, 1566 rounds and 19 excluded ambiguous boundaries. AC-2: ✓ release111-round-topology.md freezes retrieval-to-retrieval 116, verification-to-verification 111 and verification-to-task-progress 40 with implementations and upper bounds. AC-3: ✓ tests/test_round_topology.py and the real run use local files only; no model or network call. AC-4: ✓ duplicate, failed and ambiguous boundary tests pass; report states no causal token claim. Domain: real native Codex traces produced a body-free machine artifact and human-readable implementation handoff. Negative: transcript commands, prompts and outputs are absent from persisted results.
