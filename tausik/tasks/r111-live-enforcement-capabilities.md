---
slug: r111-live-enforcement-capabilities
title: "1.11: prove live host enforcement and report its limits"
status: done
epic: release-111-economy-draft
story: release111-context-and-workflow
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "bootstrap host adapters; doctor; hooks; test fixtures and isolated live-probe harness; docs"
scope_exclude: "Unrelated product features; automatic model downgrade; unapproved external publication; weakening quality gates"
relevant_files:
  - "scripts/service_doctor_enforcement.py"
  - "scripts/enforcement_evidence.py"
  - "scripts/enforcement_probe.py"
  - "bootstrap/bootstrap_codex.py"
  - "scripts/hooks/codex_write_gate.py"
  - "tests/test_codex_write_gate.py"
  - "tests/test_bootstrap_codex.py"
  - "tests/test_live_enforcement_capabilities.py"
  - "tests/test_codex_support_matrix.py"
  - "tests/test_enforcement_coverage.py"
  - "tests/test_hosts_coexist.py"
  - "tests/test_bootstrap_hooks_parity.py"
  - "tests/test_cold_start_drill.py"
  - "docs/en/doctor.md"
  - "docs/ru/doctor.md"
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - "docs/ru/research/codex-live-enforcement-2026-10-01.md"
  - "docs/ru/research/release111-economy-results.md"
  - "changelog.d/codex-write-adapter-111.md"
  - AGENTS.md
  - "tausik/tasks/public-snapshot-tests-read-excluded-files.md"
scope_paths:
  - "scripts/service_doctor_enforcement.py"
  - "scripts/enforcement_coverage.py"
  - "scripts/enforcement_evidence.py"
  - "scripts/enforcement_probe.py"
  - "tests/test_live_enforcement_capabilities.py"
  - "tests/test_codex_support_matrix.py"
  - "tests/test_enforcement_coverage.py"
  - docs
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ".tausik/planning/release-111"
  - tausik
  - "bootstrap/bootstrap_codex.py"
  - "scripts/hooks/codex_write_gate.py"
  - "tests/test_codex_write_gate.py"
  - "tests/test_bootstrap_codex.py"
  - "changelog.d/codex-write-adapter-111.md"
  - "tests/test_hosts_coexist.py"
  - "tests/test_bootstrap_hooks_parity.py"
  - AGENTS.md
  - "docs/ru/research/release111-economy-results.md"
  - "tests/test_cold_start_drill.py"
  - "tausik/tasks/public-snapshot-tests-read-excluded-files.md"
scope_tools: []
depends_on:
  - "1-11-establish-a-codex-usage-baseline-that-can"
  - r111-runtime-observation-contract
completed_at: "2026-10-01T19:53:45Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#194"
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

Address GitHub #194 by distinguishing installed hooks from effective write enforcement on Codex and the selected GLM host, so context reduction never removes the only working protection.

## Acceptance Criteria

AC-1 Doctor separately reports installed configuration, observed hook firing, proven pre-write denial and unsupported/unknown capability with host/framework version and evidence time. AC-2 Isolated live probes test Codex patch, shell and nested code-mode write routes: no-task and out-of-scope writes are denied before mutation where enforceable; allowed writes succeed. AC-3 Untrusted hooks, unsupported API, malformed payload, timeout and failed command never appear protected; limitations are named without bypassing permissions. AC-4 Bootstrap preserves user config/trust; no generic claim of arbitrary-shell understanding and no weakening QG-0/QG-2. AC-5 OWNER DECISION #414: Codex is the only live release probe; Kilo/GLM compatibility is theoretical and Claude regressions remain automated.

## Plan

[{"step": "Capture actual native PreToolUse payload and forbidden mutation evidence", "done": true}, {"step": "Normalize observed apply_patch payload with real task and scope gate reuse and behavior tests", "done": true}, {"step": "Define and implement a bounded honest policy for shell events that omit dialect", "done": true}, {"step": "Repeat trusted host-mediated forbidden and allowed matrix; verify and close only if green", "done": true}]

## Rollback

Revert this task's isolated changes and retain baseline behavior; for data changes use tested backup/restore or reversible migration.

## Journal

- 2026-10-01T16:13:05Z [implementation] — Implemented conservative local live-report reader and disposable probe capture. Doctor separates installed artifacts from patch/shell/nested outcomes, labels self-report (proof=false), rejects stale/untrusted/malformed/profile-code-drift records, warns on a reported forbidden mutation, and compacts all unknown hosts to one line. Review found local JSON is forgeable and caller reports are not host attestation; semantics were downgraded accordingly. NO-DEAD-END: focused test initially failed because _write_hooks has no filename argument; used its real settings.json shape and reran. tests/test_live_enforcement_capabilities.py + tests/test_enforcement_coverage.py + tests/test_codex_support_matrix.py: 58 passed in 1.10s. Current doctor: all six scaffolded hosts unknown; no live protection claimed.
- 2026-10-01T16:14:34Z [implementation] — Partial implementation verified green as verification_run #3240 (29/644 mapped test files; hadolint skipped as non-applicable). AC-1/AC-3 diagnostic behavior implemented conservatively, but AC-2/AC-5 require real host-mediated patch/shell/nested calls. This environment exposes Codex tools only and cannot create a disposable trusted project session or invoke Claude/Kilo; direct hook calls and synthetic fixtures are explicitly insufficient.
- 2026-10-01T18:51:13Z — Decision #414 removes the stale live Kilo/GLM prerequisite. The remaining blocker is Codex-only: a fresh session in a disposable project must trust project hooks and demonstrate pre-write denial through actual patch, shell and nested code-mode routes. The current running session cannot retroactively attest its trust handshake.
- 2026-10-01T18:55:55Z [implementation] — Resumed checkpoint #279. Created disposable project C:/Users/ayumashev/AppData/Local/Temp/tausik-live-codex-20261001-215430 using standard bootstrap --ide codex --init (35 hook matchers). Installed host reports codex-cli 0.153.4. Started native interactive TUI without model prompt or trust bypass. Host displayed directory trust request: trusting allows project-local config, hooks and exec policies to load. Awaiting explicit owner consent before Yes; trust remains unknown, all patch/shell/nested probe results not_run. No live protection claim; GLM theoretical per #414.
- 2026-10-01T19:00:12Z [implementation] — Owner authorized disposable project trust, then requested complete local Kiberza disablement. Backed up user configs; removed Kiberza hooks from Codex (5) and Claude (6), MCP entries from both (5 each). No Kiberza processes, scheduled tasks or startup entries found. Sources/data preserved. Restarting probe host to discard loaded integrations.
- 2026-10-01T19:03:00Z [implementation] — LIVE RED on Codex CLI 0.153.4: after native UI trust of all 35 project hooks (15 PreToolUse active), DB active task count=0; real functions.exec -> apply_patch/exec_command created probe-patch-no_task.txt, probe-shell-no_task.txt, probe-nested-no_task.txt. Host transcript 01a0f8d7-9c0c-7091-9501-4de0a31c7f9e. This is observed forbidden mutation, not unknown or protection.
- 2026-10-01T19:12:13Z — Owner-approved economy-first order: follow r111-bound-start-handoff with a single host-dispatch diagnosis bounded to 30-45 minutes / 20 calls. Obtain actual PreToolUse event/payload before editing adapter; stop if unavailable and name exact limit. Reuse existing disposable project and live case protocol; no repeated TUI exploration or direct-hook proof.
- 2026-10-01T19:21:57Z [implementation] — Native trusted observer captured actual nested shell PreToolUse: tool_name=Bash; tool_input.command is PowerShell Set-Content, with no shell discriminator. Offline parser comparison: Bash targets=[], PowerShell targets=[probe-nested-allowed.txt]. This disproves simple matcher mismatch as the sole cause. Actual event saved in disposable host-events.jsonl. One follow-up prompt was truncated by PTY delivery and performed no tool call; resend uses bracketed paste.
- 2026-10-01T19:23:10Z [implementation] — Diagnosis completed within bounded pass. Native observer captured (1) Bash + PowerShell Set-Content without shell identity; Bash parser returns no targets while PowerShell parser finds target; (2) apply_patch + tool_input.command containing patch text, outside Write/Edit matchers; out-of-scope .py file was created. Evidence: .tausik/planning/release-111/codex-dispatch-observation-20261001.json. Next: bounded patch payload adapter and explicit policy for ambiguous shell dialect; no generic shell-protection claim.
- 2026-10-01T19:36:11Z [implementation] — Adapter regression tests pass, but first native adapter probe still allowed patch with no task. Shell probes had malformed unquoted values and are invalid evidence. Diagnosing actual native adapter invocation; no capability promoted.
- 2026-10-01T19:41:47Z [implementation] — Live final matrix GREEN on Codex CLI0.153.4 Terra Medium: 6 native PreToolUse Promise rejections with absent targets,3 allowed mutations. Explicit JSON deny fixes observed exit2 refusal lost by Windows host. Evidence codex-final-live-20261001.json + raw tool trace. All routes code-mode; standalone and arbitrary shell unknown. Regression29 passed;ruff green;dedupe0copies. Proceeding verify.
- 2026-10-01T19:44:48Z [implementation] — Root cause: Codex command payloads differ from shared Write inputs; Windows native exit-only refusal observed as hook failure and did not block. Prevention: explicit native JSON deny plus real shared gate regressions. First verify3287 found3 stale host-parity expectations and undeclared generated AGENTS.md; fixed parity to require all shared hooks plus exactly one Codex adapter,19 focused tests pass;expanded scope. Formatter-only change verified AST-identical to live-tested adapter;exact tested source archived.
- 2026-10-01T19:48:04Z [implementation] — Verify3288 found package-import contract failure in new adapter. Added the standard own-directory import bootstrap used by sibling hooks.119 package-import and adapter tests pass. Stored exact live-tested source and explicit source delta: formatting + import-path bootstrap only; remaining AST identical. Live evidence remains tied to original disposable profile, not relabelled as a new run.
- 2026-10-01T19:53:41Z [implementation] — AC verified: 1. ✓ Doctor reader reports configuration, host/framework version, observed_at, per-route status and keeps proof=false/local_self_reported. 2. ✓ Native Codex CLI 0.153.4 matrix: patch, shell and nested routes; 6 forbidden targets absent after PreToolUse rejection and 3 allowed files created. 3. ✓ Malformed/untrusted/stale cases remain unknown in automated tests; exit-only native failure preserved as failed evidence and not protection. 4. ✓ Bootstrap preserves shared hooks plus one bounded Codex adapter; docs explicitly exclude arbitrary shell and standalone transport claims. 5. ✓ Only Codex ran live; GLM remains theoretical under Decision #414. Scoped verify #3292 passed.
