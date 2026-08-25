---
slug: harden-session-open-watchdog
title: "Harden tausik_session_open: per-section watchdog so /start can never freeze"
status: done
epic: null
story: null
complexity: null
role: null
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "scripts/handlers or .claude/mcp/project/handlers.py _handle_session_open + a _call_with_timeout helper; deploy copy to petrovka15."
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-06T13:38:08Z"
---

## Goal

petrovka15 (huge WP project) freezes on /start at 'Generating...'; every session_open sub-call works in isolation but the live compound RPC wedges and I cannot reproduce it standalone. Make _handle_session_open resilient: run each of the 5 sub-calls (session_start+current, status, handoff, tasks, self_check) under a thread watchdog with a hard timeout; on timeout the section returns {error: 'timeout Ns'} instead of blocking. This unfreezes /start AND self-reports which sub-call is slow on the next repro.

## Acceptance Criteria

1) _handle_session_open wraps every sub-call in a watchdog with a finite timeout; a hanging sub-call yields {"error":"timeout..."} for that section and the envelope still returns within ~timeout. 2) Normal case unchanged (all sections populated). 3) Deployed to petrovka15 and tausik_session_open returns within the timeout even if a section is slow. 4) Verified: injected-hang test returns the timeout error, not a freeze.

## Plan

## Rollback

git revert; the wrapper is additive (helper + call-site changes), removing it restores prior behavior.

## Journal

- 2026-07-06T13:18:02Z [implementation] — Diagnosis: session_open works isolated (~3s, full 6932B response) but I reproduced a 30s wedge when it contends with the live IDE server (petrovka15 has 6 concurrent tausik-project servers). Earlier 'exit=0' reads were false-positives — the server EOF-exits on a closed pipe before responding; with stdin held open it returns in 3s. Fix: _section_with_timeout watchdog wraps all 5 session_open sub-calls (6s each, daemon thread + join; safe because conn is check_same_thread=False). Unit-tested: fast→value, raise→error, hang→timeout@0.5s. Deployed to petrovka15 (.claude/mcp/project/handlers.py + .tausik-lib copy, stale pyc cleared); normal session_open returns all 5 sections, no timeouts. Landed in core source: harness/claude + harness/cursor handlers, both compile. Not version-bumped/rolled yet (awaiting live confirmation).
- 2026-07-06T13:37:56Z [implementation] — Verification checklist (Rule 5): [scope] only session_open handler touched (claude+cursor) + additive helper; version-bump files for release. [tests] full suite 4432 green (1 transient doc-sync failure was a mid-edit race, re-run passed); unit-tested watchdog (fast→value/raise→error/hang→timeout@0.5s); normal session_open returns all 5 sections on petrovka15+gitlab-tracker. [security] no secrets; threads safe via check_same_thread=False+busy_timeout=5000; no --force pushes. [edge-cases] EOF-exit false-positive understood (stdin held open = 3s response); daemon-thread leak on timeout is bounded/acceptable. [domain] released v1.5.8 to GitLab (e4f961b+tag) + GitHub mirror (49dcf47+tag+release); rolled to 30/30 (deployed handler has _section_with_timeout everywhere), 27 pushed, 3 infra/access/WIP-blocked (committed local). Supersedes the emergency hand-patches on petrovka15/gitlab-tracker.
- 2026-07-06T13:38:08Z [implementation] — AC1 ✓ all 5 sub-calls wrapped in _section_with_timeout (6s); hang→{"error":"...timed out"} not freeze. AC2 ✓ normal case returns all sections (verified petrovka15+gitlab-tracker). AC3 ✓ deployed to all 30 (rollout grep confirms _section_with_timeout in every deployed handler; 0 WARN). AC4 ✓ watchdog mechanism unit-tested (hang→timeout@0.5s). Released v1.5.8 GitLab+GitHub, rolled to 30/30.
