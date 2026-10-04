---
slug: define-residual-assurance-contract
title: "Define composable assurance profiles and evidence capabilities"
status: done
epic: release-1111-proportional-assurance
story: release1111-adaptive-assurance
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "Task/stack schema and migrations; stack declaration schema/loader; new pure assurance-policy module; task package projection; focused behavior and upgrade-parity tests; EN/RU assurance documentation."
scope_exclude: "Do not change /ship execution or reviewer spawning in this task. Do not add per-technology routing branches. Do not weaken risk_l3_trigger or existing security/verification gates."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/doc-map.md"
  - "docs/en/assurance.md"
  - "docs/ru/assurance.md"
  - "docs/en/stacks.md"
  - "docs/ru/stacks.md"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/assurance_policy.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v68.py"
  - "scripts/backend_schema.py"
  - "scripts/project_backend.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/service_task.py"
  - "scripts/task_assurance_fields.py"
  - "scripts/stack_registry.py"
  - "scripts/stack_schema.py"
  - "scripts/state_export.py"
  - "scripts/state_import.py"
  - "scripts/task_context_package.py"
  - "scripts/task_detail_fields.py"
  - "scripts/work_packet.py"
  - "stacks/_schema.json"
  - "stacks/ansible/stack.json"
  - "stacks/helm/stack.json"
  - "stacks/kubernetes/stack.json"
  - "stacks/terraform/stack.json"
  - "tests/test_assurance_policy.py"
  - "tests/test_stack_registry.py"
  - "tests/test_state_export.py"
  - "tests/test_state_import.py"
  - "tests/test_task_context_package.py"
  - "tests/test_work_packet.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-03T09:59:02Z"
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

Represent what a task can break, its impact, and what completed gates actually prove, so review depth is derived from residual uncertainty rather than roles or technology names.

## Acceptance Criteria

AC-1 Task and stack declarations can express composable assurance profiles, impact dimensions, and gate evidence capabilities without a technology allowlist; upgraded and fresh databases remain schema-equivalent. AC-2 A pure policy function returns profiles, impact, required evidence, observed evidence, residual gaps, selected L1/L2/L3 depth, reasons, and hard floor. AC-3 A custom Puppet-like declarative stack selects the same policy as built-in declarative stacks without changing central routing code. AC-4 Security/governance boundaries, privileged or irreversible state changes, destructive data migration, and explicit owner escalation impose a non-downgradable L3 floor. AC-5 Negative: syntax/schema-only evidence cannot satisfy policy, idempotence, rollback, behavioral, or post-condition requirements; missing metadata/evidence falls back to L2, never fabricated L1 or blanket L3. AC-6 EN/RU reference documentation defines the profiles, impact axes, capability vocabulary, extension contract, and compatibility behavior.

## Plan

[{"step": "Inventory current task, stack, gate-receipt and review data; freeze the profile, impact and evidence-capability vocabulary with compatibility rules.", "done": true}, {"step": "Add additive schema/loader support and implement the pure residual-assurance policy with deterministic reasons and hard floors.", "done": true}, {"step": "Cover built-in and custom declarative stacks, mixed profiles, missing evidence and upgrade parity with behavioral tests.", "done": true}, {"step": "Expose the policy result in the bounded task package and document the extension contract in EN/RU.", "done": true}, {"step": "Run scoped verify, dedupe audit and canonical verify; record AC evidence without integrating /ship yet.", "done": true}]

## Rollback

Revert the schema/loader/policy changes and restore the prior stack schema; migration is additive, so older code ignores new nullable/defaulted metadata and existing task/stack data remains valid.

## Journal

- 2026-10-03T09:13:40Z [planning] — Interview/specification: owner approved proportional assurance for 1.11.1. Policy must be technology-agnostic and optimize token spend by residual uncertainty after profile evidence. Project benchmark uses only natural work already performed; no paid/synthetic runs or mandatory version×model matrix. It must support longitudinal comparison after TAUSIK upgrades and naturally observed model changes. Monetary estimate is API-equivalent USD from a dated rate card; subscription quota remains separate and unattributed.
- 2026-10-03T09:18:41Z [implementation] — Step 1 done: inventoried task columns, stack schema/registry, signed verification receipts, task package projection, state import/export and schema parity. Froze additive task fields assurance_profiles/assurance_impact, stack-level profiles/default impact, per-gate evidence_capabilities, and a technology-neutral pure policy.
- 2026-10-03T09:27:23Z [implementation] — Step 2 done: added schema v68 task declarations, stack declaration validation/loader accessors, per-gate evidence capabilities, and the pure technology-neutral assurance policy with deterministic reasons and hard L3 floors.
- 2026-10-03T09:27:23Z [implementation] — Step 3 done: added behavioral tests for complete/partial evidence, mixed declarations, missing metadata, all hard L3 floors, custom Puppet-like parity with built-in Terraform, schema upgrade parity and git-state round-trip.
- 2026-10-03T09:27:23Z [implementation] — Step 4 done: bounded task package now exposes the assurance decision from task+stack declarations and the latest signed passed-gate receipt; EN/RU reference docs define vocabulary, selection, extension and compatibility.
- 2026-10-03T09:39:59Z [implementation] — Canonical verify run #3410 failed after 3688 passed, 2 skipped, 30 deselected because the larger required task context exposed a latent work_packet byte-accounting edge: omission metadata could exceed the ceiling. Fixed by recalculating exact size after every admitted unit and displacing whole prior units with explicit omission records; focused work-packet tests now pass 28/28.
- 2026-10-03T09:45:48Z [implementation] — Canonical verify run #3411 reached 4032 passed, 18 skipped and 30 deselected; its sole failure was stale docs/_generated/doc-map.md after adding the EN/RU assurance reference. Regenerated with scripts/doc_map.py --write and confirmed --check exit 0.
- 2026-10-03T09:58:33Z [implementation] — Step 5 done: scoped suites passed (237 broad focused tests plus 28 work-packet/package tests and 22 MCP/package tests), audit_pytest_dedupe.py exit 0 with 0 hollow tests, and canonical verify run #3413 passed 8 applicable gates with pytest 4459 passed, 18 skipped, 30 deselected; hadolint was not applicable to the Python scope.
- 2026-10-03T09:58:34Z [implementation] — AC verified: AC-1 ✓ schema v68 adds nullable assurance_profiles/assurance_impact; task CLI/MCP/state projection and stack schema/loader accept composable declarations and evidence capabilities; schema-upgrade parity and state round-trip tests pass. AC-2 ✓ scripts/assurance_policy.py returns profiles, normalized impact, required/observed evidence, residual gaps, L1/L2/L3 depth, deterministic reasons and hard_floor. AC-3 ✓ test_custom_puppet_declaration_uses_the_same_policy_as_builtin_terraform proves a standalone Puppet-like stack follows the built-in declarative policy with no central name branch. AC-4 ✓ parametrized behavioral tests prove non-downgradable L3 for security boundary, governance boundary, privileged, owner escalation, irreversible and destructive-data changes. AC-5 ✓ syntax/schema-only evidence leaves behavior, idempotence, rollback and postconditions residual; missing declarations return L2, never fabricated L1 or blanket L3. AC-6 ✓ docs/en/assurance.md and docs/ru/assurance.md define profiles, impact axes, capability vocabulary, extension and compatibility; doc_map --check passes. Verification ✓ run #3413: 4459 passed, 18 skipped, 30 deselected; 8 applicable gates passed, 0 failed; dedupe audit exit 0.
- 2026-10-03T09:59:01Z [implementation] — AC-1: ✓ tests/test_schema_upgrade_parity.py::TestSchemaParity::test_column_sets_are_identical ✓ tests/test_state_import.py::test_round_trip_reexport_is_byte_identical AC-2: ✓ tests/test_assurance_policy.py::test_complete_low_declarative_evidence_selects_l1 ✓ tests/test_task_context_package.py::test_package_exposes_residual_assurance_without_fabricating_l1 AC-3: ✓ tests/test_assurance_policy.py::test_custom_puppet_declaration_uses_the_same_policy_as_builtin_terraform AC-4: ✓ tests/test_assurance_policy.py::test_non_downgradable_l3_floors AC-5: ✓ tests/test_assurance_policy.py::test_syntax_and_schema_do_not_prove_declarative_behavior ✓ tests/test_assurance_policy.py::test_missing_declarations_fall_back_to_l2 AC-6: ✓ tests/test_task_context_package.py::test_mcp_task_update_accepts_assurance_declarations ✓ tests/test_doc_map.py::test_the_generated_map_is_fresh Verification: ✓ verification_run #3413
- 2026-10-03T09:59:25Z [done] — Evidence correction: AC-1 ✓ tests/test_schema_upgrade_parity.py::TestUpgradePathMatchesFreshSchema::test_column_sets_are_identical (the prior class name was mistyped; this is the collected node). Domain: a real standalone Puppet-like stack.json is accepted by StackRegistry and yields the same residual-assurance decision as built-in Terraform from declarations alone; package mode renders the decision without a technology branch, and old tasks render conservative L2.
