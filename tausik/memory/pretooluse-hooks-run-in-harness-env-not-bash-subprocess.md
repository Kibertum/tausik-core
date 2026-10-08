---
slug: pretooluse-hooks-run-in-harness-env-not-bash-subprocess
title: "PreToolUse hooks run in harness env, not Bash subprocess — inline VAR=val never reaches them"
type: gotcha
tags:
  - cross-ide
  - env
  - hooks
  - push-gate
  - ticket-flow
task: replace-broken-git-push-gate-env-bypass-with-ticke
edges: []
---

Inline `TAUSIK_X=1 some_cmd` in a Bash tool call sets the env only for some_cmd's subprocess. Claude Code / Cursor / Qwen Code all run PreToolUse hooks BEFORE the Bash subprocess starts, in the harness process — they inherit env from the harness, not from the inline VAR=val. This means env-based bypass flags (TAUSIK_ALLOW_PUSH, TAUSIK_SKIP_PUSH_HOOK as agent-set values) cannot be set inline in skills. They only work if the user started the harness with the env already set, or if the harness explicitly forwards inline env to hooks (none currently do). Use file-based authorization (single-use ticket files) for cross-IDE bypass flows. Discovered while debugging /commit step 8 contract during v1.4.0 release push.
