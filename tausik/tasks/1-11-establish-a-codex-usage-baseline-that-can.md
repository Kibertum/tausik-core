---
slug: "1-11-establish-a-codex-usage-baseline-that-can"
title: "1.11: Establish a Codex usage baseline that can prove savings without weakening quality"
status: done
epic: release-111-economy-draft
story: release111-measurement
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "Codex telemetry adapter; common usage services; CLI/MCP reporting; sanitized fixtures; baseline acceptance corpus"
scope_exclude: "No raw transcript export, implicit attribution to the active task, paid benchmark fan-out, model downgrade, or quota-to-dollar conversion."
relevant_files:
  - "scripts/usage_codex.py"
  - "scripts/usage_codex_report.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_parser_ops.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_usage_codex.py"
  - "docs/en/codex-economy-baseline.md"
  - "docs/_generated/doc-map.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/usage_codex.py"
  - "scripts/usage_codex_report.py"
  - "scripts/usage_observation.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_parser_ops.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_usage_codex.py"
  - "docs/en/"
  - "docs/ru/"
  - "tausik/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on:
  - r111-runtime-observation-contract
completed_at: "2026-10-01T15:34:45Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#193"
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

Implement native Codex response-level telemetry and freeze a bounded evaluation protocol so 1.11 decisions use measured accepted-task consumption rather than Claude counters or API-price estimates of subscription quota. Implementation authorized by owner; no paid benchmark fan-out.

## Acceptance Criteria

AC-1 Native Codex ingestion reconciles per-response records and cumulative fallback without duplication across replay, restart, fork and counter reset; partial final lines are retried and missing source data is unknown. AC-2 Shared host/provider/model contract is used; cached input and reasoning are subsets, quota windows with observation time/reset remain account-wide and are not API-dollar spend. AC-3 Task/thread attribution is explicit, past chat history and parallel-project quota are not falsely attributed; child costs and uncertain coverage are visible. AC-4 Compact CLI/MCP reports use incremental local ingestion with no raw transcript upload or consumer scripts; thresholds only on explicit user configuration. AC-5 Freeze the independent behavioral/security corpus, model/effort/speed settings, baseline revision and bounded benchmark protocol BEFORE dependent optimizations; report 6 task cases (2 per complexity), response rounds, per-kind tokens, rework/review and unknown data. AC-6 Codex live reconciliation plus fixtures for duplicate, missing, stale quota, reset, malformed and incomplete events pass; no savings claim from baseline alone.

## Plan

[{"step": "Implement Codex adapter against the shared normal form, with incremental source handling and task attribution.", "done": true}, {"step": "Reconcile native usage and quota snapshots through CLI/MCP; run negative fixtures and a live task.", "done": true}, {"step": "Freeze the matched-task corpus, independent acceptance checks and bounded Codex baseline before optimization.", "done": true}]

## Rollback

Revert only this task's changes; preserve pre-change behavior and historical evidence. For migrations verify database backup restoration.

## Journal

- 2026-10-01T15:28:50Z [implementation] — AC-1–4/6: native incremental parser and shared CLI/MCP report tested (7 behavioral tests), live 39-file capture reconciles 98 project responses; foreign/fork history excluded, task attribution unknown. AC-5 protocol frozen in docs/en/codex-economy-baseline.md; six model-driven case measurements explicitly pending release acceptance, no savings claim. NO-DEAD-END: #3232 static filesize overage was a verbose CLI option help; shortened wording without logic change.
- 2026-10-01T15:29:57Z [implementation] — NO-DEAD-END: #3233 failed generated doc-map freshness after adding baseline protocol; regenerated via scripts/doc_map.py --write. Review also caught --host initially attached to the wrong parser; corrected and upgraded integration test to use the real CLI parser plus MCP handler. 15 scoped tests passed. Domain: live source fields match fixtures; account quota is not project/task cost.
- 2026-10-01T15:31:16Z [implementation] — NO-DEAD-END: #3234 caught +129 bytes in always-advertised MCP schema. Kept the new host option but removed redundant schema prose/type (enum already constrains type) and shortened metrics description; surface ratchet now passes unchanged. Review/negative suite: 14 passed. No baseline increase or gate disablement.
- 2026-10-01T15:34:23Z [implementation] — AC-1: ✓ tests/test_usage_codex.py covers replay, restart, fork, reset and partial lines. AC-2: ✓ tests/test_usage_observation.py covers wire semantics and separate quota. AC-3: ✓ tests/test_usage_codex.py excludes other projects/inherited history; task attribution stays unknown. AC-4: ✓ real CLI parser and MCP handler share incremental report; no raw bodies persisted. AC-5: ✓ docs/en/codex-economy-baseline.md freezes 6-case protocol/revision; case measurements explicitly unmeasured pending release acceptance. Frozen checksums saved locally. AC-6: ✓ independent live reconciliation of 119 project responses matches all measured counters. Verify #3235 passed, 48 selected files; no savings claim.
