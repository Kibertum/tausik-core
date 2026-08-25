---
slug: ext-p3-enforcement-provider-ux
title: "[ext P3] Enforcement parity + provider UX (subscription, not tokens)"
status: planning
epic: vscode-extension
story: ext-program
complexity: null
role: developer
stack: null
tier: deep
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Enforcement parity + backend toggle. Qwen: gates port near-free via the Claude-identical hook contract (finish provider stub: get_active_model + transcript). Cursor: build an adapter emitting .cursor/hooks.json (beforeMCPExecution/beforeShellExecution allow/deny + failClosed) so SENAR gates hard-deny. Backend toggle UX: Claude (shell-out to local Claude Code, subscription, zero API key) vs GLM (z.ai Coding Plan env, subscription) — never become token-custodian. Kilo: accept advisory-only (re-verify no hook mechanism first).

## Acceptance Criteria

## Plan

## Rollback

## Journal
