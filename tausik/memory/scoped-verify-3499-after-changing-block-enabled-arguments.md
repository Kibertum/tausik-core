---
slug: scoped-verify-3499-after-changing-block-enabled-arguments
title: "Scoped verify #3499 after changing _block_enabled arguments"
type: dead_end
tags: []
task: bind-measured-risk-opt-out-to-target-project
edges: []
---

Approach: Scoped verify #3499 after changing _block_enabled arguments
Reason: Three bypass telemetry tests monkeypatched the old zero-argument helper and failed closed through the broad safety handler; updated those behavioral tests to accept the target-project arguments.
