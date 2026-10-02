---
slug: r111-terra-first-escalation
title: "Adopt Terra-first bounded execution with explicit Sol escalation"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "Routing policy in scripts/model_route.py and scripts/service_delegate.py; generated host guidance in bootstrap templates and harness skills; focused behavioral tests, provider docs, and one changelog fragment. Excludes telemetry redesign, active-model switching, paid benchmarks, Kiberza hooks/MCP, GitLab10, commits, pushes, and releases."
scope_exclude: "No telemetry schema or metric comparison changes; no model identity switching inside an active task; no paid benchmark or external-host integration; no Kiberza, GitLab10, commit, push, or release work."
relevant_files:
  - "scripts/model_route.py"
  - "scripts/service_delegate.py"
  - "scripts/service_task.py"
  - "scripts/model_routing_adherence.py"
  - "scripts/model_routing_session.py"
  - "scripts/model_profiles.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "harness/skills/task/SKILL.md"
  - "harness/skills/run/SKILL.md"
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - "tests/test_adaptive_model_route.py"
  - "tests/test_ow_delegate.py"
  - "tests/test_model_routing_session.py"
  - "tests/test_routing_adherence.py"
  - "tests/test_run_skill_contract.py"
  - "changelog.d/terra-first-routing-111.md"
scope_paths: []
scope_tools: []
depends_on:
  - r111-round-topology
completed_at: "2026-10-01T22:29:31Z"
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

Route eligible bounded implementation and evidence work to Terra Medium by default, using Sol only for declared complexity or failed bounded escalation conditions and Astra only for separately justified risk.

## Acceptance Criteria

AC-1 A deterministic routing table names Terra-eligible work and explicit Sol and Astra escalation predicates. AC-2 Generated guidance is consistent across supported hosts and never switches the model inside an active task identity. AC-3 At least three subsequent natural task starts record the selected route and any escalation reason. AC-4 Negative: model medians from different tasks are not presented as causal savings, and spawning a worker is refused when its startup cost exceeds the bounded remaining work.

## Plan

[{"step": "Define eligible work and escalation predicates from existing evidence", "done": true}, {"step": "Implement the routing policy and generated host guidance", "done": true}, {"step": "Add refusal for uneconomic worker startup", "done": true}, {"step": "Observe three natural starts and report route adherence without causal overclaim", "done": true}]

## Rollback

Restore the prior Sol-root and Terra-worker routing table and generated host guidance.

## Journal

- 2026-10-01T21:46:50Z [implementation] — Started after QG-0 scope declaration. Route contract will remain advisory for fresh workers and will not switch the active task identity.
- 2026-10-01T21:49:32Z [implementation] — Defined deterministic Codex fresh-worker policy: Terra for bounded simple/medium, Sol for declared complex or named bounded quality failure, Astra only with risk=high; route reasons are persisted.
- 2026-10-01T21:49:32Z [implementation] — Implemented policy, route-reason persistence, and call-budget startup refusal. Guidance updated in task/run skills and EN/RU provider docs; active task model identity remains unchanged.
- 2026-10-01T21:50:44Z [implementation] — Added bounded call-budget guard: fresh-worker startup is refused when its one-call cost exceeds remaining declared work; coordinator continues.
- 2026-10-01T21:50:44Z [implementation] — Implemented deterministic route reasons and host guidance; focused tests prove Terra default, explicit Sol/Astra escalation, and active-task identity remains advisory.
- 2026-10-01T21:50:44Z [implementation] — Scoped verification passed: pytest routing/delegation/session/adherence 65 passed; related banner/bootstrap guidance 82 passed; ruff clean. Dedupe audit completed: 0 literal copies, no new duplicate finding.
- 2026-10-01T21:51:24Z [implementation] — Bootstrap redeployed all supported profiles and bootstrap --check reports no drift. AC-3 remains intentionally open: no post-change natural task starts were created or relabelled; three independently occurring starts must each record outcome=recommended plus route_reason and any escalation_reason.
- 2026-10-01T22:05:30Z [implementation] — AC-1 verified: deterministic fresh-worker policy is covered by tests/test_adaptive_model_route.py (Terra Medium for classified bounded simple/medium; Sol for complex or named quality failure; Astra only risk=high; unclassified is advisory). AC-2 verified: all profiles redeployed and bootstrap --check clean; task/run guidance says no active identity switch. AC-4 verified: paired same-unit work estimates refuse 3>2, permit 2<3, reject incomplete/malformed input; call_budget is not used as remaining work. Routing persistence now resolves beside the backend and records current detected host/model; temp backend + foreign cwd test prevents fixture leakage. Scoped verify PASS #3330: signed receipt, gates 8 passed/1 skipped, pytest 58 passed +12 skipped over 100/654 scoped files. AC-3 remains unmet: three post-change natural starts with recorded route_reason/escalation_reason are still required; fixture rows and prior starts are excluded.
- 2026-10-01T22:07:10Z [implementation] — Correction to compact counts for verify3330: complete durable log contains25 independent pytest session summaries totaling2116 passed and12 explicitly skipped. Renderer exposed only last batch58 passed; green verdict remains valid but count was wrong. Actual regression assigned to new defect r111-verify-batch-counts before release lanes; see .tausik/verification/verify-3330.log. No natural-start evidence inferred from test-fixture route rows.
- 2026-10-01T22:26:55Z [implementation] — Domain: routing policy, supported-host guidance, and delegation economy. AC-1 PASS: scripts/model_route.py defines Terra Medium for classified bounded simple/medium work; complex or named bounded quality failures escalate to Sol, and separately declared high risk escalates to Astra. AC-2 PASS: generated task/run guidance preserves active-task identity; tests/test_model_routing_session.py and tests/test_run_skill_contract.py cover host guidance. AC-3 PASS: three natural post-change starts, excluding fixture rows: r111-verify-batch-counts at 2026-10-01T22:07:01Z, r111-verification-cycle-replay at 22:10:59Z, r111-release-quality-lanes at 22:19:15Z; each recorded codex/openai gpt-5.6-terra, medium, standard, route_reason='bounded simple/medium worker work defaults to Terra', escalation_reason=null. Batch-counts native usage independently recorded Terra Medium Standard, 12 response rounds, one attempt. AC-4 PASS: tests/test_ow_delegate.py exercises paired startup/remaining work estimate refusal and allows economical work; model medians are not claimed causal. Negative: fixture work rows and historical records are excluded from AC-3.
- 2026-10-01T22:28:50Z [implementation] — Completed routing AC evidence: AC-1/2/3/4 PASS; Domain: routing policy, supported-host guidance, and delegation economy. Three natural Codex Terra Medium Standard starts are recorded; fixture rows excluded.
- 2026-10-01T22:29:22Z [implementation] — NO-DEAD-END: verify-3326 exposed the run-skill size assertion after routing guidance grew; the guidance was shortened and later scoped verification passed. verify-3327/3328 teardown errors were concurrent SQLite/WAL lock contamination while other verification writers were active; after writers became idle, scoped receipts #3330 and #3334 passed. The cancelled follow-up rerun was stopped after pytest began and created no receipt; it is not used as evidence.
