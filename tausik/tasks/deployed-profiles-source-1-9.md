---
slug: deployed-profiles-source-1-9
title: "Синхронизировать deployed profiles с source 1.9"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Run the supported bootstrap deployment to update only installed profile copies of the three currently drifted scripts, then prove all profiles are in sync."
scope_exclude: "Do not modify scripts/ source, harness source, release metadata, tags, remote state, or user-owned .agents/."
relevant_files:
  - "bootstrap/bootstrap.py"
  - "tests/test_bootstrap_check.py"
scope_paths:
  - ".claude/scripts/gate_command_runner.py"
  - ".claude/scripts/hooks/session_metrics.py"
  - ".claude/scripts/verify_commit_ownership.py"
  - ".codex/scripts/gate_command_runner.py"
  - ".codex/scripts/hooks/session_metrics.py"
  - ".codex/scripts/verify_commit_ownership.py"
  - ".cursor/scripts/gate_command_runner.py"
  - ".cursor/scripts/hooks/session_metrics.py"
  - ".cursor/scripts/verify_commit_ownership.py"
  - ".kilo/scripts/gate_command_runner.py"
  - ".kilo/scripts/hooks/session_metrics.py"
  - ".kilo/scripts/verify_commit_ownership.py"
  - ".opencode/scripts/gate_command_runner.py"
  - ".opencode/scripts/hooks/session_metrics.py"
  - ".opencode/scripts/verify_commit_ownership.py"
  - ".qwen/scripts/gate_command_runner.py"
  - ".qwen/scripts/hooks/session_metrics.py"
  - ".qwen/scripts/verify_commit_ownership.py"
  - "bootstrap/bootstrap.py"
  - "tests/test_bootstrap_check.py"
  - "tausik/tasks/deployed-profiles-source-1-9.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T11:15:56Z"
---

## Goal

Устранить bootstrap drift в установленных профилях Claude, Codex, Cursor, Kilo, OpenCode и Qwen после изменений source scripts, чтобы task-done проверяет код, который реально загружают хосты.

## Acceptance Criteria

AC-1: bootstrap --check reports no deployed drift. AC-2: all six present profiles receive identical current copies of gate_command_runner.py, hooks/session_metrics.py and verify_commit_ownership.py. AC-3 (negative): the deployment must not alter scripts/ source, release/tag/push state or user-owned .agents/. AC-4: focused bootstrap drift tests and signed verify pass.

## Plan

[{"step": "Record the exact read-only bootstrap drift inventory.", "done": true}, {"step": "Redeploy copy-only profiles using the framework bootstrap command.", "done": true}, {"step": "Run check, focused bootstrap tests and signed verify.", "done": true}]

## Rollback

Restore the generated profile copies by rerunning bootstrap from the prior source revision.

## Journal

- 2026-09-12T11:13:11Z [implementation] — Step 1 done: read-only bootstrap --check reported exactly 18 drifted files: the same three scripts in each of Claude, Codex, Cursor, Kilo, OpenCode and Qwen profiles.
- 2026-09-12T11:13:32Z [implementation] — Step 2 done: ran supported bootstrap --ide all; all six installed profiles were regenerated from current source, including Codex. Source and user-owned .agents/ remain untouched.
- 2026-09-12T11:15:51Z [implementation] — Step 3 complete. AC-1: ✓ python bootstrap/bootstrap.py --check reports no drift. AC-2: ✓ six profile trees were regenerated from the same source. AC-3: ✓ git status shows no source/profile changes and .agents/ stayed unmodified. AC-4: ✓ 29 focused bootstrap tests passed; signed verify #2428 has ruff/pytest PASS. Domain: task-done bootstrap gate now loads and compares the deployed host copies, so it independently proves the live-profile boundary.
