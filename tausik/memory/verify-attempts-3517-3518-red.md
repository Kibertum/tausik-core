---
slug: verify-attempts-3517-3518-red
title: "Verify attempts #3517/#3518 red"
type: dead_end
tags: []
task: kilo-mcp-live-wiring
edges: []
---

Approach: Verify attempts #3517/#3518 red
Reason: Not dead ends but gate-found defects, both fixed and re-verified green in #3519: doc_coverage demanded the new check name in doctor.md en/ru; ruff S110 try-except-pass replaced with contextlib.suppress; probe initially never wrote the initialize request to stdin (caught by the speaking-stub tests, fixed before any green).
