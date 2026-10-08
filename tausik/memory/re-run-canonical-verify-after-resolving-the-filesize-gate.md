---
slug: re-run-canonical-verify-after-resolving-the-filesize-gate
title: "Re-run canonical verify after resolving the filesize gate"
type: dead_end
tags: []
task: add-cli-version-flag-and-block-session-start-on-a
edges: []
---

Approach: Re-run canonical verify after resolving the filesize gate
Reason: The MCP transport ratchet found that the direct session-start handler formatted the guard warning itself. Move the direct start plus warning renderer into update_check and make both CLI and MCP call that shared implementation.
