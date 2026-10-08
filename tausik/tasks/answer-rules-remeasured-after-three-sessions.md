---
slug: answer-rules-remeasured-after-three-sessions
title: "The answer measure is re-read three sessions after the rules reach every prompt"
status: done
epic: release-111-economy-draft
story: release111-release-proof
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "Answer-shape measurement across supported host transcript formats; existing rules"
scope_exclude: null
relevant_files:
  - "scripts/answer_shape.py"
  - "scripts/project_parser_answers.py"
  - "scripts/handoff_generate.py"
  - "scripts/call_mix.py"
  - "tausik/gates.json"
  - "tests/test_answer_rules_every_prompt.py"
  - "tests/test_call_mix.py"
  - "docs/ru/research/answer-economy-111.md"
  - "changelog.d/answer-economy-111.md"
  - "tausik/tasks/answer-rules-remeasured-after-three-sessions.md"
  - "tausik/tasks/cold-start-drill.md"
  - "tausik/tasks/schema-migrations-of-the-release-run-as-one-campaign.md"
  - "tausik/tasks/read-lever-chosen-and-measured.md"
scope_paths:
  - "scripts/answer_shape.py"
  - "tausik/gates.json"
  - "tests/test_answer_rules_every_prompt.py"
  - "docs/ru/research/answer-economy-111.md"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on:
  - "1-11-establish-a-codex-usage-baseline-that-can"
  - r111-compound-workflow-results
completed_at: "2026-10-01T18:33:11Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#202"
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

Split from answer-rules-are-in-every-prompt-not-only-consumers (1.10): the injection shipped in session #279; its effect needs sessions. Baseline on the new measure: median 162, p90 365 (newest 10 transcripts).

## Acceptance Criteria

AC-1 After 3 useful post-rule Codex sessions, metrics answers is logged against a provider-specific Codex baseline; preserve Claude 162/365 only as historical host context. AC-2 NEGATIVE: if answer size grew or completeness fell, report it and do not move a baseline to hide regression. AC-3 If it shrank with outcome/evidence/material-limitations retained, lower only the matching host baseline with provenance. AC-4 Establish Codex counters from native transcript format or state the exact unavailable capability. OWNER DECISION #414: Kilo/GLM is theoretical and not a separate quantitative prerequisite.

## Plan

[{"step": "Check native Codex answer coverage and collect at least three useful post-rule sessions.", "done": true}, {"step": "Compare median/p90 with a provider-specific baseline and completeness checks.", "done": true}, {"step": "Record the result; lower only an evidenced matching-host baseline, never disguise regression.", "done": true}]

## Rollback

Revert only this task's changes; preserve pre-change behavior and historical evidence. For migrations verify database backup restoration.

## Journal

- 2026-10-01T18:17:59Z [planning] — Owner Decision #414 narrows quantitative answer acceptance to Codex. Claude 162/365 remains historical context; Kilo/GLM is theoretical.
- 2026-10-01T18:24:05Z [implementation] — Step 1 done: native Codex response_item records identified; newest ten post-rule sessions contain nine useful sessions, without creating synthetic work.
- 2026-10-01T18:24:05Z [implementation] — Step 2 done: fresh-source metrics answers --host codex measured 35 finals: median 183, p90 256, verdict-first 45.7%, evidence median 0. The no-evidence/outcome limitation prevents a ratchet claim.
- 2026-10-01T18:25:10Z [implementation] — Step 3 done: provider-specific Codex observation recorded as provisional, not ratcheted. Claude 162/365 preserved as historical only; Kilo/GLM remains theoretical per Decision #414. Native parser behavior, fresh CLI report, bootstrap parity, lint and 42 focused tests pass.
- 2026-10-01T18:30:29Z [implementation] — AC verified: 1. Native Codex metrics logged from 10 post-rule sessions, 9 useful, 35 finals; Claude 162/365 retained only as history. 2. No cross-host baseline move: outcome/completeness unavailable and evidence median is 0, recorded explicitly. 3. Codex observation remains provisional_not_ratcheted; later same-host regression compares against it. 4. response_item user/assistant/output_text support covered by test_native_codex_answers_use_only_owner_messages_and_turn_boundaries; live CLI reports 183 median / 256 p90. Decision #414: Kilo/GLM theoretical.
