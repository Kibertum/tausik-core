---
slug: r111-compound-workflow-results
title: "1.11: fewer model round trips for the same workflow"
status: done
epic: release-111-economy-draft
story: release111-context-and-workflow
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "shared workflow services; CLI/MCP wrappers; harness skills; verification receipts; tests"
scope_exclude: "Unrelated product features; automatic model downgrade; unapproved external publication; weakening quality gates"
relevant_files:
  - "scripts/service_task.py"
  - "scripts/task_start_result.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/skills/task/SKILL.md"
  - "harness/skills/task/variants/model/haiku.md"
  - "harness/skills/task/variants/model/sonnet.md"
  - "tests/test_compound_workflow_results.py"
  - "tests/test_project_mcp.py"
  - "docs/en/context-economy.md"
  - "docs/ru/context-economy.md"
  - "docs/ru/research/compound-workflow-111.md"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/output_rollup.py"
  - "scripts/project_service.py"
  - "harness/claude/mcp/project/"
  - "harness/skills/"
  - "tests/test_session_open_handler.py"
  - "tests/test_output_rollup.py"
  - "tests/test_compound_workflow_results.py"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
  - "docs/en/"
  - "docs/ru/"
  - "scripts/task_context_package.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "tests/test_task_context_package.py"
  - "tests/test_project_mcp.py"
  - "tests/test_mcp_tool_token_cost.py"
  - "scripts/verify_cache.py"
  - "scripts/verify_cached_run.py"
  - "scripts/verify_files_hash.py"
  - "scripts/service_task.py"
  - "scripts/task_start_result.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - "1-11-establish-a-codex-usage-baseline-that-can"
  - mcp-first-rule-versus-skills-over-cli
  - r111-live-enforcement-capabilities
completed_at: "2026-10-01T17:44:19Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#198"
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

Reuse existing compound operations and move deterministic orchestration/results aggregation into shared services so fewer model turns carry identical governance guarantees.

## Acceptance Criteria

AC-1 Align AGENTS and start/task/ship skills with existing session_open and map redundant model round trips before adding new API. AC-2 Any compound operation preserves QG-0, verify-before-done, scope, audit and applicable approvals; per-step failures are explicit and partial results cannot masquerade as success. AC-3 Return compact summaries plus needed failures, preserving full evidence for targeted retrieval; small outputs do not force an extra file-read turn. AC-4 Reuse verification only when relevant input/config/gate fingerprints remain valid; invalidate on meaningful changes, never skip security verification. AC-5 Compare model-response count separately from tool-call count and include retries on Codex/GLM; no gain claim if the compound route merely hides work or costs more.
Release matrix clarification (owner, 2026-10-01): Claude Code, Kilo Code with GLM, and Codex are mandatory live acceptance targets; Codex remains the primary quantitative economy benchmark. Shared context/workflow/usage contracts apply to all three, not only fixture regression for Claude. Cursor is an additional host and OpenRouter an additional provider, never synonyms for a model or for each other. Optional Cursor/OpenRouter discovery plus thin integration has a combined ceiling of 25 extra tool calls across this release; it is not a release prerequisite. If existing adapters cannot support it without a new subsystem, stop, record capability gaps and defer that work; no automatic budget increase or claim of untested parity.
Delivery staging: first remove redundant existing service round trips on Codex and record the before/after on useful work. Limit MCP-vs-CLI exploration to existing equivalent routes; no transport rewrite. Cross-host live proof is a release-level gate.

## Plan

[{"step": "Use the MCP/CLI comparison and telemetry to select redundant workflow sequences.", "done": true}, {"step": "Implement shared deterministic operations and compact result contracts; reuse existing APIs where adequate.", "done": true}, {"step": "Exercise partial failures/cache invalidation and compare end-to-end turn counts.", "done": true}]

## Rollback

Revert this task's isolated changes and retain baseline behavior; for data changes use tested backup/restore or reversible migration.

## Journal

- 2026-10-01T17:33:09Z [implementation] — Mapped current workflow: session_open already compounds five bounded sections; task execution still requires dependent task_start then task_show(package); verify and task_done remain deliberately separate. Chosen next experiment: opt-in start-with-package on the existing task_start surface, shared serialization for CLI/MCP, no new tool.
- 2026-10-01T17:38:29Z [implementation] — Step 1 done: mapped Claude session_open (5 sections in one bounded RPC), existing structured task_done and CLI inline verify. Selected only the dependent task_start -> task_show(package) sequence; kept verify and close separate.
- 2026-10-01T17:38:30Z [implementation] — Step 2 done: added opt-in shared start_with_context envelope for CLI and MCP on the existing task_start API. QG-0 remains before activation; context failure after commit is explicit started=true/ok=false; package carries fingerprint/overflow/omissions; relevant memory is not duplicated.
- 2026-10-01T17:38:30Z [implementation] — Step 3 done: successful start+context measured by workflow contract at 2 model responses/2 tool calls before and 1/1 after; QG-0 and projection retry cases documented separately for Codex/Claude/GLM. 134 compound/docs tests + 168 verification-cache/security tests passed; MCP surface shrank 57673B -> 57636B.
- 2026-10-01T17:39:27Z [implementation] — Verify #3255 stopped before pytest because service_task.py reached 509 lines. Compressed an oversized historical projection docstring without behavior change; file is now exactly 500 lines and ruff passes. Re-running verify.
- 2026-10-01T17:43:50Z [implementation] — AC verified:\n1. Existing Claude session_open, task_done, and CLI inline verify were mapped in docs/ru/research/compound-workflow-111.md; no new MCP tool was added, and start/task/ship boundaries are documented.\n2. tests/test_compound_workflow_results.py proves QG-0 precedes activation and a post-activation projection failure returns started=true/ok=false with recovery; verify and done remain separate in the shared skill.\n3. Live deployed CLI returned one 5,466-byte envelope with a 5,333-byte bounded package, overflow=false and no duplicated relevant memory; full task_show remains targeted recovery.\n4. Existing cache/security contract stayed unchanged; 168 tests across verify_cache, verify_handle and security_sensitive passed, covering file/gate invalidation and no cache for security scope.\n5. Workflow and retry counts are recorded separately in docs/ru/research/compound-workflow-111.md: successful 2 responses/2 calls -> 1/1; QG-0 repair 3/3 -> 2/2; projection recovery 3/3 -> 2/2; transport timeout and live GLM quota savings are explicitly unclaimed.\nOfficial verify #3256 passed all applicable gates and scoped pytest over 126/647 mapped test files; hadolint was skipped as not applicable.
- 2026-10-01T17:44:09Z [implementation] — AC-2: ✓ tests/test_compound_workflow_results.py::test_context_failure_reports_committed_partial_state — partial success is explicit and task remains active. AC-3: ✓ tests/test_compound_workflow_results.py::test_start_with_context_returns_active_contract_in_one_result — active bounded contract is returned in the start result. AC-4: ✓ tests/test_verify_cache.py::TestSecurityShortCircuit::test_security_sensitive_rejects_even_with_manual_row — security scope never reuses cache.
