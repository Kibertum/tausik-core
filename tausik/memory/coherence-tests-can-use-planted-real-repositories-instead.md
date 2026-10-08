---
slug: coherence-tests-can-use-planted-real-repositories-instead
title: "Coherence tests can use planted real repositories instead of the working DB"
type: pattern
tags:
  - coherence
  - economy
  - testing
task: test-suite-is-cut-to-what-guards-behaviour
edges: []
---

1.11 audit: replace repeated whole-development-tree/DB scans with real collectors on small git repositories containing known faults. Retained 13 behavioral tests run in 1.84s; disabling duplicate detection makes retained test fail. Default suite observed 215.87s ->125.26s (one pair, not token savings). Frozen acceptance files unchanged. Do not infer that a clean repo must still contain old defects.
