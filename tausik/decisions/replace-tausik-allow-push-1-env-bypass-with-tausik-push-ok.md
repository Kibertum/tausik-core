---
slug: replace-tausik-allow-push-1-env-bypass-with-tausik-push-ok
task: replace-broken-git-push-gate-env-bypass-with-ticke
date: "2026-05-07"
edges: []
---

## Decision

Replace TAUSIK_ALLOW_PUSH=1 env bypass with `tausik push-ok` single-use ticket file (.tausik/.push_ticket.json, 60s TTL, bound to HEAD SHA + branch).

## Rationale

Inline `VAR=val cmd` Bash env never reaches PreToolUse hooks (they run in the harness process, not the Bash subprocess), so the env path was broken-by-design across every IDE — Claude Code, Cursor, Qwen Code identically. Native `permissions.ask` mode would fix Claude Code only. File-based tickets work uniformly: skill writes ticket after user 'y', hook validates schema + non-expired + HEAD-SHA match, consumes on success, re-blocks otherwise. Single-use + short TTL + HEAD-bind narrow the accidental-push window. Not a malicious-agent firewall — that role belongs to bash_firewall (force-push) and IDE permissions.
