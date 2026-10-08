---
slug: session-duration-hard-block-at-task-start-instead-of
task: null
date: "2026-04-07"
edges: []
---

## Decision

Session duration: hard block at task_start instead of warning, with session extend escape hatch

## Rationale

SENAR Rule 9.2 was only a warning — agents ignored it. Hard block forces explicit extension via session extend (CLI + MCP). Cumulative extensions tracked via events table.
