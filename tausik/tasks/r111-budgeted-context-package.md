---
slug: r111-budgeted-context-package
title: "1.11: compact stable instructions and task-specific context"
status: done
epic: release-111-economy-draft
story: release111-context-and-workflow
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "harness instructions/skills templates; context service; bootstrap generators; tests"
scope_exclude: "Unrelated product features; automatic model downgrade; unapproved external publication; weakening quality gates"
relevant_files:
  - "scripts/task_context_package.py"
  - "scripts/context_block_audit.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/hooks/session_start.py"
  - "scripts/tausik_constants.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/skills/task/SKILL.md"
  - "harness/skills/start/SKILL.md"
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_opencode.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_templates_tiers.py"
  - AGENTS.md
  - "tests/test_task_context_package.py"
  - "tests/test_context_block_audit.py"
  - "tests/test_session_start_hook.py"
  - "tests/test_memory_block.py"
  - "tests/test_context_tier.py"
  - "tests/test_claude_md_size.py"
  - "tests/test_config_module_boundary.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_bootstrap_overrides.py"
  - "tests/test_mcp_doc_tool_counts.py"
  - "tests/test_generated_rules_code_style.py"
  - "tests/test_graph_is_framework_machinery.py"
  - "tests/test_instruction_tone.py"
  - "tests/test_bootstrap_check.py"
  - "docs/en/context-economy.md"
  - "docs/ru/context-economy.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/_generated/doc-map.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/context_block_audit.py"
  - "scripts/task_context_package.py"
  - "harness/skills/"
  - "harness/overrides/"
  - "bootstrap/"
  - AGENTS.md
  - "tests/test_task_context_package.py"
  - "tests/test_context_block_audit.py"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
  - "docs/en/"
  - "docs/ru/"
  - "tests/test_config_module_boundary.py"
  - "docs/_generated/doc-map.md"
  - "tests/test_generated_rules_code_style.py"
  - "tests/test_graph_is-framework-machinery.py"
  - "tests/test_instruction_tone.py"
  - "tests/test_graph_is_framework_machinery.py"
  - "tests/test_bootstrap_check.py"
scope_tools: []
depends_on:
  - "1-11-establish-a-codex-usage-baseline-that-can"
  - r111-live-enforcement-capabilities
completed_at: "2026-10-01T17:26:13Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#197"
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

Reduce repeated TAUSIK context on Codex and GLM by emitting a small invariant contract and an on-demand bounded task package, without requiring a new memory lifecycle.

## Acceptance Criteria

AC-1 Measure injected bytes and reported model inputs by source before changing content; tool schema deferral is detected or marked unknown, never assumed. AC-2 Stable core retains no-code-without-task, goal/AC, verification, evidence, permissions and safety constraints; task package includes goals/AC, relevant paths, applicable decisions, unresolved risks and verification commands. AC-3 Skills and tools remain discoverable; use host-supported selective loading and deterministic compact responses, never silently disable required capabilities or global user plugins. AC-4 Task/context changes invalidate the package; required rules and acceptance details cannot be silently truncated to a byte target; overflow is explicit. AC-5 Measure Codex and GLM task-package usefulness and output budgets with negative omissions/conflicting or superseded memory cases; full memory tiers remain outside this task.
Release matrix clarification (owner, 2026-10-01): Claude Code, Kilo Code with GLM, and Codex are mandatory live acceptance targets; Codex remains the primary quantitative economy benchmark. Shared context/workflow/usage contracts apply to all three, not only fixture regression for Claude. Cursor is an additional host and OpenRouter an additional provider, never synonyms for a model or for each other. Optional Cursor/OpenRouter discovery plus thin integration has a combined ceiling of 25 extra tool calls across this release; it is not a release prerequisite. If existing adapters cannot support it without a new subsystem, stop, record capability gaps and defer that work; no automatic budget increase or claim of untested parity.
Delivery staging: land and measure the shared context change on Codex first. Claude/Kilo fixture compatibility is checked here; final live coverage is required by release acceptance. Completion does not wait for the GLM telemetry adapter. Preserve all mandatory instructions.

## Plan

[{"step": "Inventory actual TAUSIK-injected sources and freeze correctness/coverage checks.", "done": true}, {"step": "Generate compact invariant instructions and deterministic task-scoped context via shared service and host adapters.", "done": true}, {"step": "Compare before/after inputs and task outcomes; retain discoverability and full evidence retrieval.", "done": true}]

## Rollback

Revert this task's isolated changes and retain baseline behavior; for data changes use tested backup/restore or reversible migration.

## Journal

- 2026-10-01T17:04:14Z [implementation] — Implemented bounded task package through existing CLI/MCP task_show; compacted recurring AGENTS and SessionStart inputs; defaulted new installs to minimal; measured 17078->4602 B AGENTS, 8670->1059 B SessionStart, live package 4681/8192 B; 68 focused tests pass.
- 2026-10-01T17:17:33Z [implementation] — Verify feedback resolved without relaxing gates: MCP schema returned under the existing surface baseline; standard-tier tests now request standard explicitly; new EN/RU pages declared in and regenerated the doc map. Focused follow-ups: 1 surface ratchet, 188 generated-rule tests, 135 doc/rule tests all pass.
- 2026-10-01T17:19:18Z [implementation] — Removed a real flaky-test tax exposed twice by verify: temp cleanup now tracks only directories created by its own call instead of asserting over the process-global temp namespace while xdist workers run. Parallel bootstrap check passes 34/34.
- 2026-10-01T17:25:50Z [implementation] — AC verified: 1. ✓ Sources measured: AGENTS 17078->4602 B, SessionStart 8670->1059 B, standard rules 15533 vs minimal about 6000 B; 11 native Codex turn_context records expose 0 tools fields, so schema deferral=unknown. 2. ✓ Minimal retains task/QG0/verify/evidence/permission safety; 6007 B package carries goal, full AC, paths, active decisions, risk, verify commands. 3. ✓ existing task_show mode=package and CLI flags are documented; skills/MCP catalogs remain linked; no capability/plugin disabled; MCP schema surface ratchet passes without baseline raise. 4. ✓ fingerprint changes with task context; required overflow is explicit and untruncated; optional omissions name their range. 5. ✓ shared Codex/Claude/GLM serialization has positive and negative tests for overflow, omitted memory, superseded decisions and deterministic output; live GLM behavioral acceptance remains in the release acceptance task as declared. Verify #3251 passed over 225/646 mapped tests; hadolint skipped as unrelated.
- 2026-10-01T17:26:10Z [implementation] — AC-1: ✓ tests/test_context_block_audit.py::test_codex_schema_deferral_is_unknown_when_native_journal_has_no_signal — measured sources; absent native signal stays unknown.
- 2026-10-01T17:26:11Z [implementation] — AC-2: ✓ tests/test_task_context_package.py::test_package_carries_required_intent_and_commands — required intent, paths and verification survive.
- 2026-10-01T17:26:11Z [implementation] — AC-3: ✓ tests/test_task_context_package.py::test_mcp_task_show_exposes_package_without_adding_a_tool — package stays discoverable on existing MCP surface.
- 2026-10-01T17:26:11Z [implementation] — AC-4: ✓ tests/test_task_context_package.py::test_required_overflow_is_explicit_and_never_truncates_ac — Negative: small budget returns complete AC plus overflow.
- 2026-10-01T17:26:12Z [implementation] — AC-5: ✓ tests/test_task_context_package.py::test_superseded_decision_is_excluded — Domain: shared serialization excludes stale decisions; omission test covers bounded memory.
