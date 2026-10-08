---
slug: add-memory-only-governance-profile
title: "Add an explicit memory-only governance profile for infrastructure projects"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: complex
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Project-level governance profile resolution; hook filtering and host bootstrap propagation; profile-aware generated instructions; EN/RU configuration and release documentation; behavioral/bootstrap parity tests."
scope_exclude: "Do not auto-select reduced governance from stack detection, remove MCP servers or stored data, change default full enforcement, alter assurance semantics, touch the four protected active release tasks, publish, commit or push."
relevant_files:
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap_governance.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_codex.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_opencode.py"
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_templates_tiers.py"
  - "tests/test_governance_profile.py"
  - "tests/test_rules_generator_warning_parity.py"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/hooks.md"
  - "docs/ru/hooks.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
assurance_profiles:
  - executable
assurance_impact: "{\"blast_radius\":\"broad\",\"data_change\":\"none\",\"governance_boundary\":true,\"level\":\"high\",\"owner_escalation\":false,\"privileged\":false,\"reversibility\":\"reversible\",\"security_boundary\":false}"
depends_on: []
completed_at: "2026-10-04T09:57:31Z"
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

Let a project explicitly keep TAUSIK memory, MCP, logs and codebase RAG while removing task, scope, verify and session hook ceremony in a bootstrap-stable, truthfully documented profile, without weakening projects merely because they use an infrastructure stack.

## Acceptance Criteria

AC-1 A documented project config selects memory-only explicitly; full remains the default and invalid values fail safe to full or are refused. AC-2 Bootstrap for every hook-capable supported host retains only memory_pretool_block.py and memory_posttool_audit.py registrations in memory-only, while keeping TAUSIK project MCP, codebase RAG, logs and stored memory available. AC-3 Generated AGENTS.md/CLAUDE.md truthfully names memory-only and no longer instructs agents to perform task, scope, verify, QG-0/QG-2 or session rituals; it retains memory routing and project-local knowledge rules. AC-4 Re-bootstrap is idempotent and does not restore heavy hooks; the default full profile remains behaviorally unchanged. AC-5 Negative: Ansible/Terraform/Kubernetes/Helm detection alone never weakens governance, malformed/unknown profile values cannot silently disable enforcement, and tests cover host parity plus bootstrap drift. AC-6 EN/RU configuration and release notes explain the opt-in, retained capabilities and lost guarantees; scoped tests, dedupe audit and canonical verify pass.

## Plan

[{"step": "Define the explicit fail-safe profile contract and exact retained/lost surfaces against every host bootstrap path.", "done": true}, {"step": "Implement one shared profile resolver, hook filtering and host propagation while preserving the full default byte-for-byte behavior.", "done": true}, {"step": "Generate truthful compact memory-only instructions and keep project MCP, codebase RAG, logs and stored memory available.", "done": true}, {"step": "Add negative/default/idempotence/host-parity tests and reconcile EN/RU configuration plus changelogs.", "done": true}, {"step": "Run focused tests, dedupe audit, bootstrap and canonical verify; obtain L3 review, record full evidence and close QG-2.", "done": true}]

## Rollback

Remove the memory-only profile selector and filtering/template branches; bootstrap again to restore the unchanged full hook and instruction profile. No database migration or project data rewrite is involved.

## Journal

- 2026-10-04T09:37:47Z [implementation] — Defined governance_profile as an explicit root config with only full and memory-only values. Default is full; invalid/non-string values stop bootstrap before mutation; stack detection is not an input. Memory-only retains exactly the two memory hook scripts on hook-capable hosts, removes OpenCode QG-0 plugin, keeps both MCP servers/RAG/data, and emits a compact truthful instruction body naming lost guarantees.
- 2026-10-04T09:43:52Z [implementation] — Implemented a shared explicit profile resolver and hook-declaration filter. Claude/Qwen/Codex receive the filtered declaration; Codex omits its write adapter; OpenCode removes its QG-0 plugin. Default full calls the original paths and is byte-equivalent in generated rule bodies and hook declarations.
- 2026-10-04T09:43:53Z [implementation] — Implemented a compact truthful memory-only rules body plus managed profile switching for generated CLAUDE.md, AGENTS.md, Cursor, Qwen and OpenCode rules. Custom files remain byte-exact with a warning. Behavioral tests prove MCP project and codebase-rag survive while only the memory route/audit pair remains; 141 focused bootstrap/profile tests pass.
- 2026-10-04T09:44:03Z [implementation] — Added fail-safe/default/stack-noninference tests; exact shared/Codex/Qwen memory hook tests; MCP retention tests; OpenCode plugin-removal test; generated-rule switching, custom preservation and idempotence tests. Updated EN/RU configuration, hooks guidance and changelogs. Ruff passed and the focused bootstrap/profile slice passed 141 tests.
- 2026-10-04T09:52:42Z [implementation] — L3 review #55 found one documentation contradiction: the legacy blanket preservation claim did not distinguish context/output changes from governance-profile switching. Updated EN/RU configuration docs to state the exact boundary: TAUSIK-marked generated rules switch idempotently, custom files are preserved with a warning. Focused regression: 310 passed, 16 skipped.
- 2026-10-04T09:57:18Z [implementation] — AC-1: ✓ bootstrap_config.resolve_governance_profile accepts only explicit full or memory-only, defaults to full, refuses malformed or unknown values, and test_profile_is_explicit_fail_safe_and_never_inferred_from_stack proves Ansible metadata alone cannot select the reduced profile. AC-2: ✓ bootstrap_governance.MEMORY_ONLY_HOOKS centralizes the exact memory_pretool_block.py and memory_posttool_audit.py pair; shared Claude/Kilo/Cursor hooks, Codex, Qwen and OpenCode bootstrap paths consume the profile while retaining project MCP, codebase RAG, database logs and memory. Covered by test_shared_and_codex_memory_only_hooks_retain_exactly_the_memory_pair, test_qwen_keeps_mcp_and_only_memory_hooks, and test_opencode_removes_qg0_plugin_but_keeps_mcp_and_memory_rules. AC-3: ✓ the generated memory-only rule pack explicitly names retained MCP/RAG/memory and lost task, scope, verify, QG-0/QG-2, session, receipt, secret-scan, push and usage guarantees; test_memory_only_rules_name_retained_and_lost_guarantees_without_rituals checks that heavy rituals are absent. AC-4: ✓ profile-aware write_generated_rules switches only TAUSIK-marked generated files, preserves custom files with warning, is idempotent, and delegates full-profile rendering to the existing generator path; test_generated_rules_switch_profiles_idempotently_but_custom_rules_survive and test_codex_rerun_replaces_heavy_hooks_and_preserves_foreign_keys cover rollback/rebootstrap behavior. A real full-profile bootstrap completed successfully and kept 36 Codex matchers. AC-5: ✓ Negative evidence: infrastructure stack detection is not an input to profile resolution; invalid profile values raise instead of weakening enforcement; foreign configuration keys and custom rules survive; memory-only reruns do not restore heavy hooks; OpenCode's managed QG-0 plugin is removed only under explicit memory-only. The seven behavior tests plus the generator-warning parity meta-test cover these boundaries. AC-6: ✓ EN/RU configuration, hooks and changelogs describe the opt-in, retained capabilities and lost guarantees. Focused regressions passed twice (94 and 141), final docs/profile slice passed 310 with 16 skipped, ruff passed, audit_pytest_dedupe.py reported 0 COPY and 282 PARALLEL groups with no unable-to-fail tests, canonical verify #3440 PASS recorded 1615 passed, 16 skipped, 51 deselected across 83/659 scoped test files with 63 direct-import subject tests and 8 applicable gates passed; hadolint was not applicable. Domain evidence: explicit project-owner configuration; all supported hook-capable bootstrap adapters; generated agent rules; MCP/RAG/memory retention; full-profile rollback; EN/RU public contract. Negative evidence: no automatic Ansible/Terraform/Kubernetes/Helm downgrade, no silent invalid-value fallback to reduced governance, no custom-rule overwrite, no foreign-key loss, no heavy-hook resurrection, and no claim that memory-only retains QG/security/accounting guarantees. L3 external review #56 by opus, separate from author gpt-5.6-sol, approved with 0 critical, 0 high and 0 warnings after the EN/RU preservation wording was corrected.
- 2026-10-04T09:57:25Z [implementation] — Final verification complete: focused suites, ruff, dedupe audit, full-profile bootstrap, canonical verify #3440 and independent L3 review #56 all passed.
- 2026-10-04T09:57:42Z [done] — Post-closure test-reference normalization for the QG-2 record: tests/test_governance_profile.py::test_profile_is_explicit_fail_safe_and_never_inferred_from_stack; tests/test_governance_profile.py::test_shared_and_codex_memory_only_hooks_retain_exactly_the_memory_pair; tests/test_governance_profile.py::test_memory_only_rules_name_retained_and_lost_guarantees_without_rituals; tests/test_governance_profile.py::test_generated_rules_switch_profiles_idempotently_but_custom_rules_survive; tests/test_governance_profile.py::test_qwen_keeps_mcp_and_only_memory_hooks; tests/test_governance_profile.py::test_codex_rerun_replaces_heavy_hooks_and_preserves_foreign_keys; tests/test_governance_profile.py::test_opencode_removes_qg0_plugin_but_keeps_mcp_and_memory_rules; tests/test_rules_generator_warning_parity.py::TestGeneratorWarnings::test_none_of_them_is_silent. These are the exact behavior and negative-boundary citations summarized in the preceding AC evidence.
