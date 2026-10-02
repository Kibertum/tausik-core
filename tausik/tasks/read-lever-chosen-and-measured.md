---
slug: read-lever-chosen-and-measured
title: "A lever for the read category is chosen from metrics calls and measured before/after"
status: done
epic: release-111-economy-draft
story: release111-context-and-workflow
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "Existing read-call metrics and measured read/retrieval lever; tests; harness guidance"
scope_exclude: null
relevant_files:
  - "scripts/call_mix.py"
  - "harness/skills/task/SKILL.md"
  - "tests/test_call_mix.py"
  - "changelog.d/read-fanout-111.md"
  - "tausik/tasks/read-lever-chosen-and-measured.md"
scope_paths:
  - "scripts/call_mix.py"
  - "harness/skills/"
  - "tests/test_call_mix.py"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on:
  - "1-11-establish-a-codex-usage-baseline-that-can"
  - r111-compound-workflow-results
completed_at: "2026-10-01T18:34:52Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#200"
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

Split from reading-code-costs-a-third-of-calls (1.10): the measurement shipped; the lever needs sessions. BEFORE (session #279, newest 10 transcripts, 198 closed tasks): median calls simple 14 (read 2), medium 29 (read 7), complex 50 (read 18); read 30.8% of attributed calls.

## Acceptance Criteria

AC-1 One Codex-first lever for the read category is chosen from metrics calls and shipped. AC-2 After 3+ post-change Codex sessions, calls and model responses per task by complexity are re-measured and logged against the provider-specific BEFORE cohort. AC-3 NEGATIVE: if the Codex read median does not fall, say so and revert the lever or keep it with a measured reason. AC-4 Count model responses separately from tool calls and include full task/rework cost; batching independent reads must retain every needed finding. Claude medians are historical context. OWNER DECISION #414: Kilo/GLM is theoretical in 1.11 and is not a separate live quantitative prerequisite.

## Plan

[{"step": "Select one Codex-first read-category lever from the fixed provider-specific baseline.", "done": true}, {"step": "Implement one bounded change with source-completeness checks and host-separated response/tool metrics.", "done": true}, {"step": "After at least three post-change Codex sessions, re-measure by complexity and retain or revert with evidence.", "done": true}]

## Rollback

Revert only this task's changes; preserve pre-change behavior and historical evidence. For migrations verify database backup restoration.

## Journal

- 2026-10-01T18:09:59Z [implementation] — Implementation evidence: shared harness/skills/task/SKILL.md carries the universal compound-read rule. scripts/call_mix.py now separates Claude-compatible and native Codex cohorts, discovers Codex sessions by exact cwd metadata, parses bounded tool metadata without persisting bodies, and reports model responses separately from tool calls. Current pre-lever Codex cohort (newest 10 transcripts, 3 closed tasks): medium n=1 responses/tools/read=25/25/14; complex n=2 medians 104.5/104.5/47.5; read share 46.6%. Claude historical baseline remains 2/7/18 read medians and 30.7% share.
- 2026-10-01T18:09:59Z [implementation] — Lever selected from fixed baseline: one host-native compound fan-out for independent searches/bounded reads, with every result inspected and dependent follow-ups kept separate. Parallel tool calls alone were rejected as insufficient because they reduce model rounds but not read-tool count. Kilo/GLM sample is unavailable because live GLM generation is blocked by HTTP 402 (task r111-glm-host-usage-adapter).
- 2026-10-01T18:11:12Z [implementation] — Verification run #3259 passed all executed gates: ruff, filesize, format, dedupe, class surface, bootstrap drift, doc coverage and scoped pytest (51 tests); hadolint skipped as non-applicable. Step 3 remains pending three post-lever sessions.
- 2026-10-01T18:16:59Z [implementation] — Plan repaired after status tokens were accidentally written as step text. Owner Decision #414 narrows quantitative acceptance to Codex; Kilo/GLM remains theoretical.
- 2026-10-01T18:30:45Z [implementation] — Metric honesty fix: transcript-side task done is only an attempt, so reports now require DB status=done before accepting a window. This prevents gate-blocked work from appearing closed. Focused call-mix suite run after the change.
- 2026-10-01T18:34:23Z [implementation] — Step 3 / negative evidence: three useful Codex tasks completed after lever activation. Baseline native cohort (medium 25 calls/14 reads; complex median 104.5/47.5; three-task overall median 51/25). Post cohort: complex r111-glm-host-usage-adapter 72/41; medium cold-start-drill 40/17; simple answer-rules-remeasured 41/25 with no matching simple baseline. Post overall median 41 calls and 25 reads: calls -19.6%, read median unchanged. Keep the bounded compound-read rule because the behavior test proves 2 independent reads become 1 call with both findings retained; claim no measured task-level saving.
- 2026-10-01T18:34:47Z [implementation] — AC verified: AC-1 shared compound-read rule shipped. AC-2 three completed post-change Codex tasks measured by complexity with separate responses/tools. AC-3 NEGATIVE: post read median remained 25; rule retained only for its directly tested 2-to-1 call behavior and receives no release saving claim. AC-4 every finding is retained in the behavior test; Claude remains historical and GLM theoretical per Decision #414.
