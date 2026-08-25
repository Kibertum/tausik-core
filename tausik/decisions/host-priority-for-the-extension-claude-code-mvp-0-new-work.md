---
slug: host-priority-for-the-extension-claude-code-mvp-0-new-work
task: null
date: "2026-07-08"
edges: []
---

## Decision

Host priority for the extension: Claude Code (MVP, ~0 new work, full gates) -> Qwen Code (Claude-identical hook contract, gates port nearly free; official VS Code Companion) -> Cursor (real hard gates via own hooks.json since 1.7, needs adapter + Open VSX publishing) -> Kilo (advisory-only, no hook mechanism found; lowest value, do last). Enforcement 'gate parity' investment is best spent on the Cursor hooks.json adapter, NOT Kilo.

## Rationale

Session #102 external research: Qwen Code borrows Claude Code's exact hook JSON contract (PreToolUse deny + exit-2), test-pinned parity already in bootstrap_qwen.py. Cursor 1.7 (Oct 2025) added hooks.json with beforeMCPExecution/beforeShellExecution allow/deny + failClosed. Kilo (Cline lineage) has no hook mechanism found -> SENAR gates only advisory there. Irony: Kilo (the originally-named target) is the WEAKEST for SENAR enforcement. Open item: re-verify Kilo hooks before final Kilo scoping.
