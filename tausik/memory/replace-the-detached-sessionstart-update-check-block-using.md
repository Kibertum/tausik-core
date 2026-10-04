---
slug: replace-the-detached-sessionstart-update-check-block-using
title: "Replace the detached SessionStart update-check block using copied console context."
type: dead_end
tags:
  - encoding
  - hook
task: add-cli-version-flag-and-block-session-start-on-a
edges: []
---

Approach: Replace the detached SessionStart update-check block using copied console context.
Reason: The patch context contained mojibake and did not match the UTF-8 source. Re-read exact line-bounded source and patch smaller function ranges.
