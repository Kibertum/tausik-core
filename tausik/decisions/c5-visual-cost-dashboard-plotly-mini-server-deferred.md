---
slug: c5-visual-cost-dashboard-plotly-mini-server-deferred
task: v14c-visual-cost-dashboard
date: "2026-05-07"
edges: []
---

## Decision

C5 visual-cost-dashboard (Plotly mini-server) DEFERRED — текстовый `tausik metrics --cost` достаточен; Plotly/Dash dep нарушает CLAUDE.md stdlib rule + memory dead-end #27 (ChromaDB rejection precedent).

## Rationale

Альтернатива уже работает в production (`tausik metrics --cost`). Добавление heavy dep (Plotly+Dash) ради cosmetic visualization не оправдано: stdlib-only — load-bearing constraint фреймворка (echoed в memory dead-end #27 для ChromaDB). Если когда-нибудь понадобится — opt-in extras-pip-install pattern.
