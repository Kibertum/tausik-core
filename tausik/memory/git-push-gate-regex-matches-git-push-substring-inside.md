---
slug: git-push-gate-regex-matches-git-push-substring-inside
title: "git_push_gate regex matches `git push` substring inside heredoc commit message bodies"
type: gotcha
tags:
  - false-positive
  - heredoc
  - hooks
  - push-gate
  - regex
task: replace-broken-git-push-gate-env-bypass-with-ticke
edges: []
---

scripts/hooks/git_push_gate.py uses a regex that anchors on whitespace/punctuation before `git push` to avoid matching `--force-push`-like substrings. But a HEREDOC commit message body is part of the `tool_input.command` string, and a phrase like `inline VAR=val git push` inside the body trips the regex (whitespace-anchored). Result: `git commit -m "$(cat <<EOF ... git push ... EOF)"` is BLOCKED with a misleading "no push ticket" message. Workaround: rephrase the body to avoid the literal sequence (e.g. `<push-cmd>`, `git-push` with hyphen). Better long-term fix: parse the command with shlex and only check the first/non-heredoc tokens. Captured 2026-05-07 during v1.4.0 release.
