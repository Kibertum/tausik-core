---
slug: guard-host-context-budget-before-session-reopen
title: "Guard host context budget before session reopen"
status: done
epic: null
story: null
complexity: complex
role: null
stack: null
tier: moderate
call_budget: 28
defect_of: null
scope: "Host-thread identity, session lifecycle, native Codex usage thresholds, checkpoint/fresh-window handoff, supported-host guidance and focused lifecycle tests."
scope_exclude: "No automatic deletion of host threads, no provider quota formula inference, no Kiberza, GitLab10, commit, push or release."
relevant_files:
  - "scripts/service_host_context.py"
  - "scripts/usage_codex_report.py"
  - "scripts/project_cli.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "harness/claude/mcp/project/tools_extra.py"
  - "harness/skills/start/SKILL.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/workflow.md"
  - "docs/ru/workflow.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "changelog.d/host-context-budget-111.md"
  - "tests/test_host_context_budget.py"
  - "tests/test_usage_codex.py"
scope_paths:
  - scripts
  - "harness/skills"
  - "docs/en"
  - "docs/ru"
  - tests
  - changelog.d
  - AGENTS.md
  - CLAUDE.md
scope_tools: []
depends_on: []
completed_at: "2026-10-02T08:58:33Z"
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

Tie TAUSIK lifecycle to the real host thread and stop or hand off before accumulated context makes each model return disproportionately expensive.

## Acceptance Criteria

AC-1 Same host thread cannot present a reopened TAUSIK session as fresh context. AC-2 Configurable response/input/context advisory and hard budgets emit checkpoint plus a copy-ready fresh-window prompt before the ceiling; reject session reopen at the hard threshold. AC-3 Host adapters degrade explicitly when native usage is unavailable; invalid budget configuration returns an error rather than silently disabling enforcement. AC-4 Behavioral tests cover same-thread reopen, new thread, boundary thresholds and unavailable usage without exact-string or existence-only checks. AC-5 Changelog and EN/RU workflow guidance explain the rule.

## Plan

[{"step": "Measure host-thread/context signals already available without transcript injection", "done": true}, {"step": "Define advisory and hard handoff thresholds plus same-thread reopen semantics", "done": true}, {"step": "Implement one canonical service policy with thin CLI/MCP and skill guidance", "done": true}, {"step": "Replay an over-budget lifecycle, scoped verify, document and close", "done": true}]

## Rollback

Remove the budget guard and generated guidance; existing session lifecycle remains available.

## Journal

- 2026-10-01T22:58:02Z [planning] — Priority 1. Starts in a fresh host window. It must distinguish TAUSIK session ids from the host thread/context identity and emit a copy-ready handoff before further model returns become expensive.
- 2026-10-01T23:10:27Z [implementation] — Defined advisory/hard semantics, same-thread reopen behavior and explicit fail-open degradation.
- 2026-10-01T23:10:27Z [implementation] — Measured available host identity and native usage signals without transcript content injection.
- 2026-10-01T23:10:27Z [implementation] — Steps 1-2 evidence: existing Codex native journal exposes CODEX_THREAD_ID plus per-response total input/cached/output; service session rows already bind host_session_id. Defined defaults advisory 24 responses/2.5M cumulative input/140k latest context and hard 32/4M/180k; any available signal crosses, invalid ordering fails, unavailable native usage degrades explicitly.
- 2026-10-01T23:12:24Z [implementation] — Canonical service policy, thin transports, guidance, docs and changelog implemented.
- 2026-10-01T23:12:24Z [implementation] — Step 3 evidence: implemented service_host_context as the single policy; CLI and MCP call it as thin wrappers. Codex adapter filters the native journal by current thread and exposes latest context. /start skill, EN/RU workflow/config/MCP docs and bilingual changelog fragment updated. Focused suite: 136 passed; ruff green; pytest dedupe audit reports 0 copy groups.
- 2026-10-02T08:58:23Z [implementation] — AC verified: AC-1 tests/test_host_context_budget.py::test_same_thread_reopen_is_not_fresh_but_a_new_thread_is. AC-2 advisory/hard checkpoint and prompt tests plus live hard replay session #282: checkpoint_saved=true, session immediately closed. AC-3 unavailable and invalid-config behavioral tests. AC-4 1026 passed/12 skipped/23 deselected in scoped verify #3341; ruff passed; dedupe audit 0 copy groups. AC-5 EN/RU workflow, configuration, MCP docs and changelog.d/host-context-budget-111.md updated.
- 2026-10-02T08:58:44Z [done] — AC-1: ✓ tests/test_host_context_budget.py::test_same_thread_reopen_is_not_fresh_but_a_new_thread_is. AC-2: ✓ tests/test_host_context_budget.py::test_advisory_saves_one_checkpoint_and_returns_a_new_window_prompt and live session #282 checkpoint_saved=true/ended_at set. AC-3: ✓ tests/test_host_context_budget.py::test_missing_native_usage_is_explicit_and_never_claims_fresh_context. AC-4: ✓ verification_run #3341: 1026 passed, 12 skipped, 23 deselected; tests/test_host_context_budget.py::test_invalid_budget_configuration_fails_before_opening_a_session is the Negative case. AC-5: ✓ docs/en/workflow.md, docs/ru/workflow.md and changelog.d/host-context-budget-111.md reviewed. Domain: native Codex replay measured 53 responses, 6026274 cumulative input and 149538 latest context; policy wrote and immediately closed checkpoint-only session #282, so a hard old thread did not continue.
