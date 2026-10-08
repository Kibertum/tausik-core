---
slug: kilo-glm-acceptance-through-z-ai-glm-flash-latest
title: "Kilo GLM acceptance through ~z-ai/glm-flash-latest"
type: dead_end
tags: []
task: r111-glm-host-usage-adapter
edges: []
---

Approach: Kilo GLM acceptance through ~z-ai/glm-flash-latest
Reason: Kilo Gateway returned HTTP 402 before generation: zero credits and model isFree=false. The database contains a failed zero-token GLM record, not a completed response; adapter now exposes failed_responses and glm_completed_responses separately.
