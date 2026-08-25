---
slug: v15-ow-core
title: "Orchestrator-worker core — delegate primitive, sub-agent contract, gating"
status: done
epic: v15-orchestrator-worker
---

Decision-anchored (Decision: auto-switch = orchestrator-worker pattern, NOT platform fight). Main session = Opus coordinator (planning/AC/review). Tasks with complexity<=medium auto-spawn as sub-agents via the Agent tool with model=recommended — the only programmatic model-selection mechanism Claude Code exposes. Aligned with Anthropic orchestrator-workers pattern. Decomposed from the former single task v15-orchestrator-worker-pattern into 6 tracked tasks: (1) task delegate CLI primitive, (2) sub-agent skill profile + handoff contract, (3) scope hard-gate for delegated sub-agent, (4) hook integration to recognize a delegated task, (5) summary-back via task_log, (6) docs + integration tests.
