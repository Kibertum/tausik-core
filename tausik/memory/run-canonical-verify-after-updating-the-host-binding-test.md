---
slug: run-canonical-verify-after-updating-the-host-binding-test
title: "Run canonical verify after updating the host-binding test"
type: dead_end
tags: []
task: add-cli-version-flag-and-block-session-start-on-a
edges: []
---

Approach: Run canonical verify after updating the host-binding test
Reason: The cross-cutting encoding gate found the new --version subprocess test inherited the parent code page. Pin UTF-8 explicitly, matching the CLI wrapper contract, then rerun the scoped gate.
