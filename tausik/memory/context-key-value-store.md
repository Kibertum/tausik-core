---
slug: context-key-value-store
title: "Context key-value store"
type: pattern
tags:
  - context
  - kv-store
task: null
edges: []
---

ctx set/get/list/delete for ephemeral key-value pairs. Stored in 'context' table with UPSERT semantics. Used for session-scoped data that doesn't fit memory or decisions. Keys are plain strings, values are text. Not FTS-indexed.
