---
slug: tausik-1-11-1-exposes-a-cli-version-flag-and-every-session
task: add-cli-version-flag-and-block-session-start-on-a
date: "2026-10-03"
edges: []
---

## Decision

TAUSIK 1.11.1 exposes a CLI version flag and every session start performs or consumes an explicitly fresh authoritative version check; if a newer release exists, startup stops and tells the user how to update.

## Rationale

The user requires stale installations to fail visibly before session work begins. Exact handling of network failures, malformed responses, prereleases, privacy, and existing opt-out behavior remains part of the planned task's acceptance contract.
