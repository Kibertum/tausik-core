---
slug: r111-glm-host-usage-adapter
title: "1.11: GLM usage through a host adapter and the common ledger"
status: done
epic: release-111-economy-draft
story: release111-measurement
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "host-specific usage adapter; usage services and reporting; tests; provider support docs"
scope_exclude: "Unrelated product features; automatic model downgrade; unapproved external publication; weakening quality gates"
relevant_files:
  - "scripts/usage_kilo.py"
  - "scripts/usage_observation.py"
  - "scripts/service_token_metrics.py"
  - "tests/test_usage_kilo.py"
scope_paths:
  - "scripts/usage_kilo.py"
  - "scripts/usage_observation.py"
  - "scripts/service_token_metrics.py"
  - "tests/test_usage_kilo.py"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
  - "docs/en/"
  - "docs/ru/"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_parser_ops.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_usage_observation.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - r111-budgeted-context-package
  - r111-compound-workflow-results
  - r111-runtime-observation-contract
completed_at: "2026-10-01T18:16:33Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#196"
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

Ship GLM through Kilo Code in 1.11 using the common usage contract. Claude Code and Codex are separate mandatory host targets; OpenRouter is an optional provider adapter under the shared bounded compatibility budget.

## Acceptance Criteria

AC-1 Record Kilo Code/provider/model versions and obtain sanitized real-format usage events through a supported interface or versioned local transcript adapter; no consumer-project scripts. AC-2 Input/cache/output counters reconcile to the source, repeated reads and resumes do not duplicate usage, missing reasoning/quota are unknown. AC-3 GLM never inherits Claude/OpenAI rates or subscription formulas; a documented API cached-token field is not proof that the host exposes it. AC-4 CLI and MCP compact reports share implementation and cover unavailable-source behavior. AC-5 OWNER DECISION #414: theoretical Kilo/GLM acceptance is sufficient for 1.11; record the paid live-call failure and do not claim completed live parity. Codex is the primary quantitative release target.

## Plan

[{"step": "Identify selected GLM host and observable surfaces; capture sanitized fixtures and a capability report.", "done": true}, {"step": "Implement a thin adapter over the shared normal form, with incremental ingestion and explicit unavailable capabilities.", "done": true}, {"step": "Reconcile real Kilo usage and document theoretical GLM acceptance without paid generation.", "done": true}]

## Rollback

Revert this task's isolated changes and retain baseline behavior; for data changes use tested backup/restore or reversible migration.

## Journal

- 2026-10-01T17:48:53Z [implementation] — Step 1 evidence: installed Kilo VS Code extension is 7.8.1; supported current surface is read-only local SQLite at ~/.local/share/kilo/kilo.db (official Kilo session-history docs). Live DB schema stores per-message providerID/modelID and disjoint input/output/reasoning/cache read/cache write counters; Kilo source confirms input/output exclude cache/reasoning. Six real local sessions exist, but zero assistant responses identify a GLM model, so live GLM parity remains unproven. Kilo CLI executable is not on PATH; adapter will use the documented DB interface and explicit unavailable status.
- 2026-10-01T17:58:01Z [implementation] — Corrected Step 1 evidence: bundled Kilo CLI 7.8.1 exists inside the VS Code extension but is not on PATH; its documented SQLite surface is the adapter source. Live DB has 6 sessions/234 assistant responses and zero GLM responses.
- 2026-10-01T17:58:02Z [implementation] — Steps 1-2 evidence: added read-only incremental Kilo SQLite adapter and common CLI/MCP dispatch. Kilo counters are disjoint and normalize to input=plain+cache_read+cache_write, output=plain+reasoning. Three behavioral tests cover resume/dedup, missing data/unavailable source, cache privacy and CLI/MCP parity. Live non-GLM Kilo session reconciled exactly; Windows live run exposed and fixed a SQLite handle leak.
- 2026-10-01T18:02:13Z [implementation] — Step 3 partial evidence: live Kilo 7.8.1 GLM smoke reached provider kilo/model ~z-ai/glm-flash-latest, but Gateway returned HTTP 402 before generation (zero credits; catalog isFree=false). Adapter correctly reports responses=1, failed_responses=1, glm_responses=1, glm_completed_responses=0 and reconciled zero tokens. Full live GLM start/report/verify/resume remains pending credits or z.ai subscription configuration.
- 2026-10-01T18:15:16Z [implementation] — Owner accepted Kilo/GLM theoretically and made Codex the primary target (Decision #414). AC-5 is satisfied by honest boundary evidence: Kilo 7.8.1 format and live database reconciled; paid GLM generation failed with HTTP 402; no completed-live-parity claim.
- 2026-10-01T18:15:52Z [implementation] — AC-1 pass: Kilo 7.8.1 SQLite adapter records sanitized provider/model/version. AC-2 pass: incremental resume/dedup and live session aggregate reconciliation; missing values remain unknown. AC-3 pass: no inherited rates, quota or savings claims. AC-4 pass: shared CLI/MCP report and unavailable-source tests. AC-5 pass per owner Decision #414: theoretical acceptance; HTTP 402 live failure recorded and completed parity not claimed.
- 2026-10-01T18:16:00Z [implementation] — AC verified: 1. ✓ Kilo 7.8.1 sanitized provider/model/version adapter. 2. ✓ resume/dedup/live aggregate reconciliation; missing stays unknown. 3. ✓ no inherited rates/quota/savings. 4. ✓ shared CLI/MCP plus unavailable-source tests. 5. ✓ owner Decision #414 accepts theory; HTTP 402 failure recorded, no completed parity claim.
- 2026-10-01T18:16:14Z [implementation] — AC-1: ✓ tests/test_usage_kilo.py::test_cli_and_mcp_share_kilo_report. AC-2: ✓ tests/test_usage_kilo.py::test_incremental_resume_reconciles_without_persisting_conversation. AC-3: ✓ tests/test_usage_kilo.py::test_unavailable_and_missing_reasoning_are_explicit. AC-4: ✓ tests/test_usage_kilo.py::test_cli_and_mcp_share_kilo_report. AC-5: ✓ Decision #414 and live HTTP 402 evidence; completed parity explicitly not claimed.
- 2026-10-01T18:16:25Z [implementation] — AC-1 (identity and sanitized source): ✓ tests/test_usage_kilo.py::test_cli_and_mcp_share_kilo_report
- 2026-10-01T18:16:26Z [implementation] — AC-2 (resume and reconciliation): ✓ tests/test_usage_kilo.py::test_incremental_resume_reconciles_without_persisting_conversation
- 2026-10-01T18:16:26Z [implementation] — AC-3 (unknown quota and no pricing): ✓ tests/test_usage_kilo.py::test_unavailable_and_missing_reasoning_are_explicit
- 2026-10-01T18:16:27Z [implementation] — AC-4 (CLI and MCP parity): ✓ tests/test_usage_kilo.py::test_cli_and_mcp_share_kilo_report
- 2026-10-01T18:16:27Z [implementation] — AC-5 (owner theoretical acceptance): ✓ Decision #414; HTTP 402 failure remains explicit and completed parity is not claimed.
