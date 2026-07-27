---
slug: brain-telemetry-through-best-effort-logger
title: "Brain telemetry through best-effort logger"
type: pattern
tags:
  - "brain,metrics,r14,telemetry"
task: null
edges: []
---

scripts/brain_metrics_log.py uses sqlite3 timeout=2.0 + try/except wrapping; failures silently dropped so brain operations are never blocked. Resolves project DB via CLAUDE_PROJECT_DIR > cwd > scripts dir. Pattern: telemetry must NEVER block the operation it observes.
