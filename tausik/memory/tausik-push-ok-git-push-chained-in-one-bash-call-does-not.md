---
slug: tausik-push-ok-git-push-chained-in-one-bash-call-does-not
title: "`tausik push-ok && git push` chained in one Bash call does NOT work — hook runs before shell"
type: gotcha
tags:
  - commit
  - hooks
  - push-gate
  - ship
  - skills
task: replace-broken-git-push-gate-env-bypass-with-ticke
edges: []
---

PreToolUse hooks fire BEFORE the shell parses or executes the chained command. So `tausik push-ok && git push` in a single Bash tool call → hook sees `git push` substring, ticket file does not yet exist (push-ok hasn't run), hook blocks. The chain never executes. Correct usage: TWO separate Bash tool invocations — first `tausik push-ok` (creates ticket), then `git push` (hook reads + consumes ticket). Skills /commit step 8 + /ship currently document the broken `&&` chain — needs follow-up doc fix. Verified 2026-05-07.
