---
slug: route-ship-by-residual-assurance
title: "Route ship review by residual assurance"
status: done
epic: release-1111-proportional-assurance
story: release1111-adaptive-assurance
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "Canonical review dispatcher and service/MCP/CLI exposure; /ship and /review canonical skills plus generated host copies; review recording/telemetry; task package preview; focused integration tests and EN/RU workflow docs."
scope_exclude: "Do not alter task implementation model routing unrelated to review. Do not remove deterministic verify gates. Do not claim a token saving percentage before natural project comparison."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/doc-map.md"
  - "docs/en/assurance.md"
  - "docs/en/cli-quality.md"
  - "docs/en/severity-scale.md"
  - "docs/en/stacks.md"
  - "docs/en/workflow.md"
  - "docs/ru/assurance.md"
  - "docs/ru/cli-quality.md"
  - "docs/ru/severity-scale.md"
  - "docs/ru/stacks.md"
  - "docs/ru/workflow.md"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/subagents/tausik-external-reviewer.md"
  - "harness/skills/review/SKILL.md"
  - "harness/skills/ship/SKILL.md"
  - "scripts/assurance_policy.py"
  - "scripts/backend_crud.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v68.py"
  - "scripts/backend_migrations_v69.py"
  - "scripts/backend_schema.py"
  - "scripts/project_backend.py"
  - "scripts/project_cli_review.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_review.py"
  - "scripts/project_parser_task.py"
  - "scripts/review_routing.py"
  - "scripts/review_separation.py"
  - "scripts/risk_l3_trigger.py"
  - "scripts/service_review_gate.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "scripts/stack_registry.py"
  - "scripts/stack_schema.py"
  - "scripts/state_export.py"
  - "scripts/state_import.py"
  - "scripts/task_assurance_fields.py"
  - "scripts/task_context_package.py"
  - "scripts/task_detail_fields.py"
  - "scripts/work_packet.py"
  - "stacks/_schema.json"
  - "stacks/ansible/stack.json"
  - "stacks/helm/stack.json"
  - "stacks/kubernetes/stack.json"
  - "stacks/terraform/stack.json"
  - "tests/test_assurance_policy.py"
  - "tests/test_review_routing.py"
  - "tests/test_review_separation.py"
  - "tests/test_risk_l3_trigger.py"
  - "tests/test_stack_registry.py"
  - "tests/test_state_export.py"
  - "tests/test_state_import.py"
  - "tests/test_task_context_package.py"
scope_paths: []
scope_tools: []
assurance_profiles:
  - executable
  - migration
assurance_impact: "{\"blast_radius\":\"broad\",\"data_change\":\"non_destructive\",\"governance_boundary\":true,\"level\":\"high\",\"reversibility\":\"conditional\"}"
depends_on: []
completed_at: "2026-10-03T13:33:18Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Make /ship spend zero or one reviewer call on ordinary work and reserve multi-agent deep review for explicit or critical cases, without weakening existing hard L3 escalation.

## Acceptance Criteria

AC-1 /ship consumes the canonical assurance policy: L1 performs the profile checklist plus deterministic gates with zero reviewer subagents; L2 uses one focused fresh-context reviewer; normal L3 uses one different-model external reviewer; multi-agent L3-deep runs only for an explicit deep audit or configured extreme hard floor. AC-2 Actual L1/L2/L3 records, author/reviewer identity, selected profile, reasons, hard floor, reviewer invocation count, and available usage are persisted consistently; same-family separate-context review is never recorded as L3. AC-3 Mixed work takes the maximum applicable floor while retaining profile-specific checks; executable code added by research/docs work cannot hide in a cheaper lane. AC-4 Current measured-high closure escalation remains effective and can raise an earlier L1/L2 route to L3 before close. AC-5 The task package previews the chosen route and missing inputs before review, and every supported host consumes the same policy result rather than reimplementing it in skill prose. AC-6 Negative cases cover missing metadata, skipped evidence gates, security/critical paths, failed verification after substantive repair, reviewer HIGH/CRITICAL findings, and unavailable different-model review; none silently closes at a lower level. AC-7 Existing explicit /review behavior remains available as a forced deep audit, and EN/RU workflow documentation explains auto versus forced review.

## Plan

[{"step": "Consume the canonical policy through one dispatcher shared by CLI, MCP and host skills; define L1, L2, L3 and deep execution contracts.", "done": true}, {"step": "Integrate /ship and /review, preserving forced deep review and the measured-high closing escalation.", "done": true}, {"step": "Persist actual review depth, profile, reasons, model separation, invocation count and available usage.", "done": true}, {"step": "Exercise mixed tasks, critical paths, skipped evidence, unavailable reviewers and post-fix escalation across supported hosts.", "done": true}, {"step": "Regenerate host artifacts, update EN/RU workflow docs, run scoped and canonical verification, and record measured fan-out before/after.", "done": true}]

## Rollback

Revert dispatcher and skill integration to unconditional full review; persisted review records and assurance metadata remain readable and can be ignored by the older workflow.

## Journal

- 2026-10-03T09:13:40Z [planning] — Interview/specification: owner approved proportional assurance for 1.11.1. Policy must be technology-agnostic and optimize token spend by residual uncertainty after profile evidence. Project benchmark uses only natural work already performed; no paid/synthetic runs or mandatory version×model matrix. It must support longitudinal comparison after TAUSIK upgrades and naturally observed model changes. Monetary estimate is API-equivalent USD from a dated rate card; subscription quota remains separate and unattributed.
- 2026-10-03T12:58:37Z [implementation] — QG-0 verified in package mode: goal and seven acceptance criteria are defined; complex-task scope, exclusions, rollback metadata and five-step plan passed task_start. Starting implementation against the completed residual assurance contract while preserving the four unrelated active tasks and the intentionally dirty worktree.
- 2026-10-03T13:06:57Z [implementation] — Early scoped tests: 79 passed, 5 failed. All failures are compatibility ordering in project_cli_review: the new generic validator masked the existing SENAR Rule 4 diagnostics, and a legacy test adapter accidentally produced the conservative L2 package instead of its explicit L1 record. Fixing by preserving the existing L3 separation validator as the first authority and limiting the legacy fallback to adapters without the real backend query surface.
- 2026-10-03T13:12:46Z [implementation] — Canonical dispatcher is shared by package/MCP projection, CLI and host skill instructions.
- 2026-10-03T13:12:46Z [implementation] — Negative and cross-host routing cases are covered.
- 2026-10-03T13:12:46Z [implementation] — Ship/review integration and closing escalation completed.
- 2026-10-03T13:12:46Z [implementation] — Step 1 done: added technology-neutral review_routing dispatcher; task package and CLI consume the same route with L1=0, L2=1 fresh-context, L3=1 different-model, and explicit/configured L3-deep=7 calls.
- 2026-10-03T13:12:46Z [implementation] — Step 2 done: /ship now executes required.review_route and re-reads it before close; /review is the forced deep surface; measured-high L3 escalation remains in risk_l3_trigger and failed HIGH/CRITICAL L3 records no longer satisfy it.
- 2026-10-03T13:12:46Z [implementation] — Step 3 done: schema v69 persists actual depth, profiles, reasons, hard floor, author/reviewer models, context, invocation count, route JSON, HIGH findings and available usage; separation now recognizes supported Claude/OpenAI/GLM profile identities.
- 2026-10-03T13:12:46Z [implementation] — Step 4 done: behavioral tests cover mixed profiles, missing metadata, skipped/partial evidence, hard L3 boundaries, measured-high escalation, unavailable/same-family reviewer, verification failure, HIGH/CRITICAL findings and post-repair verification. Focused runs: 84 passed; integration/migration/skill run: 169 passed with 8 slow deselected; provider/separation run: 91 passed; risk run: 52 passed.
- 2026-10-03T13:12:46Z [implementation] — Structured review recording and telemetry completed.
- 2026-10-03T13:13:49Z [implementation] — Final scoped verification before TAUSIK gates: 342 passed, 8 slow deselected. audit_pytest_dedupe.py completed with 0 COPY groups, 282 PARALLEL groups, and no test function unable to fail. Canonical skills regenerated for active Codex profile; cross-host bootstrap/profile coverage is green. Fan-out contract changed from unconditional 6 reviewers (7 in deep mode) to L1=0, L2=1, normal L3=1, explicit/configured L3-deep=7; no token-saving percentage is claimed.
- 2026-10-03T13:22:19Z [implementation] — First tausik_verify run #3415 failed before pytest: ruff_format named 5 files, bootstrap_drift named 68 deployed copies, and scope omitted 6 reviewer-fix files. Applied ruff format, redeployed every installed host with bootstrap --ide all, and widened relevant_files to the exact added docs/subagent/service paths.
- 2026-10-03T13:23:48Z [implementation] — Second verify run #3416 failed before pytest because service_task_done.py reached 547 lines over the 500-line gate. Extracted the canonical closure check unchanged into service_review_gate.py and retained the task_done call as a three-line gate boundary.
- 2026-10-03T13:25:10Z [implementation] — Third verify run #3417 again stopped before pytest: service_task_done.py remained 508 lines. Moved the closure gate import to module scope and compacted existing module/refutation comments; ruff-formatted result is 498 lines. External reviewer approved the extracted closure gate; passing review recorded after fixes.
- 2026-10-03T13:26:05Z [implementation] — Fourth verify run #3418 passed seven static gates and ran 416 tests before migration-chain failure: v69 ALTERed reviews in a sparse schema_version=35 fixture where the optional table was absent. Added CREATE TABLE IF NOT EXISTS for the legacy reviews base before additive columns; real upgrades remain no-op on the create, sparse fixtures now migrate.
- 2026-10-03T13:33:07Z [implementation] — Verification complete: scoped suite 351 passed, 8 slow deselected; pytest dedupe audit 0 COPY, 282 PARALLEL, all 7829 test functions able to fail; canonical verify #3419 passed 4605 tests, 18 skipped, 30 deselected across 249/656 files with 220 direct-import subject tests. Review fanout changed from unconditional standard review of 6 calls (deep 7) to residual route L1=0, L2=1, normal L3=1, explicit/configured L3-deep=7; no token-saving percentage claimed. Independent different-model L3 review #49 approved.
- 2026-10-03T13:33:14Z [implementation] — AC verified: 1. Canonical review_routing and ship skill route L1/L2/L3/deep from residual assurance; tests/test_review_routing.py plus verify #3419. 2. Schema v69, CLI persistence, model separation and structured review records #45-#49 persist actual depth, profiles, reasons, models, context, invocation count and usage. 3. Mixed-profile union is covered by policy and route tests without any technology allowlist. 4. Measured HIGH findings raise the current route and latest-review selection prevents an older clean review from masking newer HIGH or CRITICAL findings. 5. Task package exposes required.review_route; bootstrap --ide all regenerated host artifacts; profile integration tests passed. 6. Negative and QG2 integration tests cover task and stack hard floors, missing evidence, unavailable reviewers, failed findings and post-repair re-review; canonical verify passed 4605, skipped 18, deselected 30. 7. Explicit /review remains forced deep; EN/RU assurance, workflow, CLI, severity and changelog documentation describe the contract and limitations. Scoped tests passed 351 with 8 slow deselected. audit_pytest_dedupe reported 0 COPY, 282 PARALLEL, and all 7829 test functions able to fail. Independent different-model L3 review #49 approved.
- 2026-10-03T13:33:28Z [done] — AC-1: ✓ scripts/review_routing.py and ship skill implement L1=0, L2=1, L3=1 different-model, deep=7 only explicit/configured; route tests and verify #3419 pass. AC-2: ✓ schema v69 and review CLI persist depth, identities, profiles, reasons, hard floor, context, invocations and usage; separation tests reject same-family L3. AC-3: ✓ policy/route mixed-profile tests take the maximum floor and retain every profile check; no stack allowlist exists. AC-4: ✓ service review gate combines current measured HIGH escalation and latest-review logic prevents older clean records masking newer HIGH/CRITICAL. AC-5: ✓ package exposes required.review_route and missing_inputs; bootstrap --ide all regenerated supported hosts from canonical skill/policy. AC-6: ✓ negative tests cover missing metadata/evidence, task and stack hard floors, failed verify/repair, HIGH/CRITICAL findings and unavailable different-model review. AC-7: ✓ explicit review stays forced deep; EN/RU assurance/workflow/CLI/severity docs distinguish auto and forced routes. Domain: ✓ real CLI package, route, record and QG2 closure exercised; independent gpt-6-astra L3 review #49 approved; verify #3419 passed 4605 tests, 18 skipped, 30 deselected. Scoped: 351 passed, 8 slow deselected. Dedupe: 0 COPY, 282 PARALLEL; 7829/7829 tests can fail.
