---
slug: "1-11-distinguish-model-speed-subscription-cost-from-token"
title: "1.11: distinguish model/speed subscription cost from token double counting"
type: context
tags:
  - codex
  - economy
  - release-1.11
task: null
edges: []
---

Owner asked whether Astra doubles tokens. Official sources fetched 2026-10-01: https://learn.chatgpt.com/docs/pricing says Fast consumes included subscription limits 2.5x Standard for same model (purchased credits 2x), Astra Ultrafast 8x included (credits6x); no fixed Astra-to-Sol subscription multiplier established. https://learn.chatgpt.com/docs/models recommends GPT-6.1 Sol when available for complex coding, Astra for hardest work, lower reasoning for bounded tasks. Current native project snapshot:98 Astra responses, input11815495 including cached11389952 (~96.4%), output79184 including reasoning13510. These subsets must not be added twice. Snapshot does not establish current speed mode or task-specific quota consumption. Recommendation, not an owner-approved configuration change: Sol Standard/default reasoning for routine 1.11 implementation, selective Astra escalation, compare accepted-task cost including retries. Root model cannot be changed with available agent tools.
