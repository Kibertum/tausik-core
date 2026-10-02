---
slug: r111-runtime-observation-contract
title: "1.11: separate host, provider, model and measured usage"
status: done
epic: release-111-economy-draft
story: release111-measurement
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/model_profiles.py; host/model detection; scripts/backend_schema.py and migrations if required; usage services; tests"
scope_exclude: "Unrelated product features; automatic model downgrade; unapproved external publication; weakening quality gates"
relevant_files:
  - "scripts/usage_observation.py"
  - "tests/test_usage_observation.py"
  - "tests/test_model_profiles.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/usage_observation.py"
  - "tests/test_usage_observation.py"
  - "tests/test_model_profiles.py"
  - "changelog.d/"
  - "tausik/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-10-01T15:21:46Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#195"
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

Provide a provider-neutral observation contract used by Codex and GLM integrations without replacing unknown identity with Claude or equating usage tokens with subscription quota.

## Acceptance Criteria

AC-1 Host/client version, provider, model ID, reasoning and speed mode, source timestamp and format version are independent nullable fields; observed, configured and unknown identities are distinguishable. AC-2 Normalize total input, cached-input subset, output and reasoning-output subset only when source semantics support them; preserve unknown and cache-write semantics without Anthropic default multipliers. AC-3 Define project/thread/response/task identities and attribution confidence; account quota snapshots remain a separate time series with freshness and reset. AC-4 Contract fixtures cover Codex, GLM via selected host and Claude regression; duplicate, partial and unsupported records never produce fabricated zero or default Claude. AC-5 Existing history is migrated compatibly or remains explicitly legacy; no raw prompts, credentials or transcript bodies enter portable state.
AC-6 Distinguish transport-compatible shape from semantics using common fixtures for native Codex, Claude/Anthropic, Kilo+GLM and OpenRouter-compatible usage; preserve reported model/provider identity, optional cache/reasoning fields and unavailable quota. No full host×provider Cartesian matrix is required.
Release matrix clarification (owner, 2026-10-01): Claude Code, Kilo Code with GLM, and Codex are mandatory live acceptance targets; Codex remains the primary quantitative economy benchmark. Shared context/workflow/usage contracts apply to all three, not only fixture regression for Claude. Cursor is an additional host and OpenRouter an additional provider, never synonyms for a model or for each other. Optional Cursor/OpenRouter discovery plus thin integration has a combined ceiling of 25 extra tool calls across this release; it is not a release prerequisite. If existing adapters cannot support it without a new subsystem, stop, record capability gaps and defer that work; no automatic budget increase or claim of untested parity.
Delivery rule: implement only the observation contract required for native Codex accounting first; reuse Claude normalization. No generic plugin registry, dashboard or pricing service is prerequisite. Start with offline/source-counter checks, not paid model calls.
AC-7 NEGATIVE: invalid or negative token counters and inconsistent cached/input totals are rejected; absent provider/model/usage remains unknown rather than zero or Claude.

## Plan

[{"step": "Inspect current host/provider detection and ledger consumers; define versioned normal form and capability flags.", "done": true}, {"step": "Implement the smallest common normalizer with backward-compatible storage and source adapters.", "done": true}, {"step": "Run cross-provider contract and negative tests; record schema/upgrade implications.", "done": true}]

## Rollback

Revert this task's isolated changes and retain baseline behavior; for data changes use tested backup/restore or reversible migration.

## Journal

- 2026-10-01T15:19:29Z [implementation] — Steps 1–2: implemented provider-neutral versioned observations without DB migration; legacy ledger unchanged. Explicit wire semantics, nullable counters, identity provenance, safe field allowlist and duplicate/conflict handling. Scoped regression: 28 passed in 0.39s (new contracts + model profiles).
- 2026-10-01T15:20:58Z [implementation] — AC-1–7 ✓ tests/test_usage_observation.py and tests/test_model_profiles.py: 35 passed. Explicit wire semantics/identity provenance, invalid and absent counters, dedup conflict, quota separation and field allowlist verified. Legacy DB unchanged. Review: no model inference or price conversion. Fresh CLI verify #3229 passed; MCP process stale after deployment, using documented CLI fallback.
- 2026-10-01T15:21:45Z [implementation] — NO-DEAD-END: verify #3228 failed because the already-running MCP process retained pre-deployment code. The gate prescribed fresh CLI; #3229 and #3230 passed there. Initial QG-0 refusal was negative-scenario keyword recognition, corrected by explicit invalid-counter AC. No product test failure was hidden.
