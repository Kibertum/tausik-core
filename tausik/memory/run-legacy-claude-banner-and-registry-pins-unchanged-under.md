---
slug: run-legacy-claude-banner-and-registry-pins-unchanged-under
title: "Run legacy Claude banner and registry pins unchanged under Codex"
type: dead_end
tags:
  - host-routing
  - tests
  - verification
task: r111-adaptive-model-routing
edges: []
---

Approach: Run legacy Claude banner and registry pins unchanged under Codex
Reason: The tests inherited the current Codex model and old host sets, so they failed despite correct provider-aware behavior. Made Claude tests declare TAUSIK_AGENT_MODEL and updated the measured host-registry pin; also extracted resume routing after the filesize gate exposed service_task.py growth.
