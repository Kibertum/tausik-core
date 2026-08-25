---
slug: meta-kv-delete-with-meta-delete-not-empty-string-tombstone
title: "meta kv: delete with meta_delete, not empty-string tombstone; sibling aggregates share defensive posture"
type: convention
tags:
  - defensive
  - kv
  - meta
  - review
task: v15p-ow-mem-review-fixes
edges: []
---

Two conventions from review of the OW/memory work: (1) To clear a `meta` kv key use `be.meta_delete(key)` (DELETE FROM meta WHERE key=?), NOT `meta_set(key, "")` — the empty-string trick reads back falsy but leaves accumulating tombstone rows and couples correctness to meta_get's falsy-check. (2) Sibling aggregate helpers must share the same failure posture: build_memory_block now wraps backend calls in try/except→'' to match build_compact_memory_tail (was crash-prone while its sibling was crash-safe) — when you add a defensive guard to one of a pair, audit the other. Also: when a function fans out N list fetches with per-kind bounds, give each its own max param (max_contexts was wrongly coupled to max_decisions).
