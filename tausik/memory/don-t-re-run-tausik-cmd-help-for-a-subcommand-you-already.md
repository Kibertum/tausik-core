---
slug: don-t-re-run-tausik-cmd-help-for-a-subcommand-you-already
title: "Don't re-run 'tausik <cmd> --help' for a subcommand you already used this session"
type: convention
tags: []
task: null
edges: []
---

The 'read references/project-cli.md / don't guess args' rule covers UNKNOWN args — not a license to re-probe every call. If a subcommand's signature was already used (or is known), call it directly. Reach for --help / project-cli.md only for genuinely unknown args, once, then cache for the session. (session #88: re-ran 'memory add --help' after already using memory add — wasted a call.)
