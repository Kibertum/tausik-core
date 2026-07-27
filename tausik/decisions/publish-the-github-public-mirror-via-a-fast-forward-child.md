---
slug: publish-the-github-public-mirror-via-a-fast-forward-child
task: fix-hook-cp1252-unicode-crash
date: "2026-07-06"
edges: []
---

## Decision

Publish the GitHub public mirror via a fast-forward child commit off the existing orphan root, not a force-pushed fresh orphan.

## Rationale

The firewall blocks git push --force and its bypass env can't reach the harness-run hook. A child of the scrubbed root (f380a2e→7c311e8→49dcf47) is fast-forward (no force, no bypass), exposes zero private history (parent is itself a parentless scrubbed root), and only touches already-public files. Trade-off: mirror history grows past a single commit, but the security invariant (no monorepo paths / site history / secrets) holds.
