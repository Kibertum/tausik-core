---
slug: remove-the-local-sys-import-together-with-gate-progress
title: "Remove the local _sys import together with gate-progress streaming"
type: dead_end
tags: []
task: bound-agent-validation-output-to-durable-artifacts
edges: []
---

Approach: Remove the local _sys import together with gate-progress streaming
Reason: A later budget advisory in the same handler still wrote to _sys.stderr. It now uses the existing module-level sys import; no progress callback is restored.
