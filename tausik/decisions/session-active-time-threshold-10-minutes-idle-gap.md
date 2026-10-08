---
slug: session-active-time-threshold-10-minutes-idle-gap
task: null
date: "2026-04-25"
edges: []
---

## Decision

Session active-time threshold = 10 minutes idle gap, configurable via .tausik/config.json

## Rationale

10 min covers normal context-switching (read docs, brief slack, bio break) without inflating duration on AFK breaks. 15 min too lenient — real AFK sessions get under-counted. 5 min too aggressive — common pauses look like AFK. Make it config-tunable so users with different workflows can adjust without code change.
