---
slug: session-handoff-for-context-transfer
title: "Session handoff for context transfer"
type: pattern
tags:
  - context
  - handoff
  - sessions
task: null
edges: []
---

Sessions track start/end/summary + handoff JSON. session_last_handoff() returns the most recent handoff for context continuity between Claude Code conversations. Handoff is free-form JSON stored in sessions table. Skills /start and /end read/write handoffs automatically.
