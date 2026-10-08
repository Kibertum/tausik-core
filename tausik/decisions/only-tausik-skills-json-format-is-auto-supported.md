---
slug: only-tausik-skills-json-format-is-auto-supported
task: skill-install-system
date: "2026-04-07"
edges: []
---

## Decision

Only tausik-skills.json format is auto-supported. Incompatible repos get error message + link to adaptation guide.

## Rationale

Trying to auto-detect and adapt 3+ different formats (Claude-native, plugin-monorepo, etc.) is fragile and untestable. Better to define our standard and provide a clear adaptation guide. User can fork and adapt any repo.
