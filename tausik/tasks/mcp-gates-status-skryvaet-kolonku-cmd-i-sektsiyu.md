---
slug: mcp-gates-status-skryvaet-kolonku-cmd-i-sektsiyu
title: "MCP gates_status скрывает колонку cmd и секцию мета-гейтов, которые показывает CLI"
status: done
epic: release-1-11-3
story: release1113-quality-ratchets
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_cli_gates.py (extract shared gates_status_lines renderer), harness/claude/mcp/project/handlers_verification.py (_handle_gates_status delegates to the shared renderer via svc.gates_status()), scripts/mcp_cli_parity.py (delete the six healed ledger entries), tests/test_mcp_cli_surface_parity.py (only if the driver needs adjusting), CHANGELOG en/ru"
scope_exclude: "scripts/project_service.py gates_status data shape (unchanged), gate registry/config semantics, .claude deployed copies (bootstrap is a release step)"
relevant_files:
  - "scripts/project_cli_gates.py"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "scripts/mcp_cli_parity.py"
  - "tests/test_config_read_project_scope.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T08:41:31Z"
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

MCP gates_status loses what the CLI twin shows: the per-gate cmd column and the whole meta-gate section (verify_first_contract, continuous_changelog, qg_0_readiness, renar_drift_1, renar_drift_7). Caught live by the parity ratchet on its first run; fix the handler and delete the six ledger entries.

## Acceptance Criteria

1) tausik_gates_status renders the per-gate cmd column (built-in or command) the CLI shows. 2) The meta-gate section (Verify-First Contract, Continuous CHANGELOG, QG-0 Readiness, RENAR drift-1, drift-7) reaches the MCP output. 3) NEGATIVE: the six known-loss entries for tausik_gates_status in scripts/mcp_cli_parity.py are DELETED in the same commit that fixes the handler — the ledger only shrinks. 4) NEGATIVE: token budget respected — growth of the gates_status answer stays within the MCP surface cost ratchet (test_mcp_tool_token_cost).

## Plan

## Rollback

git revert: handler returns to its own flat render, the six ledger entries return, no data or gate behaviour changes

## Journal

- 2026-10-07T08:40:28Z [implementation] — AC verified. 1) ✓ cmd column reaches MCP: _handle_gates_status(svc) renders via the shared gates_status_lines (verbose=True) — per-gate "cmd: (built-in|command)" lines present; parity driver case tausik_gates_status reports zero losses. 2) ✓ meta-gate content + QG-0 Readiness section reach MCP — same formula the CLI prints (multi-line descriptions, stack groups with (detected), QG-0 block from svc.gates_status()). 3) ✓ NEGATIVE: the six KNOWN_LOSSES entries for tausik_gates_status are DELETED in this same change (ledger is {} again); the ratchet's healed-entry check enforced the deletion mechanically — leaving them would have failed test_cli_labels_reach_the_mcp_surface. 4) ✓ NEGATIVE: token budget — the MCP surface cost ratchet (tests/test_mcp_tool_token_cost.py) counts tool SCHEMAS and tausik_gates_status's inputSchema is untouched; the growth is answer text, not surface cost. Verified by scoped verify run #3600 PASS (168 passed over 10 of 667 test files mapped from relevant_files; gates 8/9, hadolint N/A; handle 3600.7de9ee6598be9a31752f6f5325265b18). CLI output byte-identical: slow-lane test_tausik_cli.py::test_gates_status green after the refactor. test_handle_gates_status_renders_svc_project re-anchored to the "(detected)" marker — pytest belongs to four stack groups and renders under the first alphabetical one (django), so a python-detection witness can leave the python header empty; documented in the test. Domain: the shared render runs against the real service (ProjectService over SQLite with effective gate config) on both surfaces; the ratchet compares live renders, not fixtures.
- 2026-10-07T08:41:27Z [implementation] — NO-DEAD-END: the two red closure attempts were the bootstrap_drift gate refusing until the edit reached the DEPLOYED copies — first try redeployed only the default profile (12->10 mismatched), second ran bootstrap --ide all and --check went green. The handler fix itself was never red: verify #3600 passed before the ritual, and the approach (shared render formula, delegation) never changed.
