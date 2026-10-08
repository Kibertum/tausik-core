---
slug: session-active-time-uses-clip-not-exclude-semantics
title: "Session active-time uses CLIP (not EXCLUDE) semantics"
type: convention
tags:
  - rule-9.2
  - sessions
  - v1.4-polish
task: v14b-session-active-time
edges: []
---

As of v14b-session-active-time (v1.4 polish): Session active time = Σ min(Δ, idle_threshold) over inter-event gaps. A long AFK gap contributes EXACTLY threshold (default 600s/10min), not 0. Implementation: scripts/backend_session_metrics.py::compute_active_seconds — SQL CASE branch is THEN ? (clipped) NOT THEN 0 (excluded). compute_active_minutes is a thin rounding wrapper. When changing this code, remember the historical EXCLUDE semantics shipped in v1.3 and was flipped in v1.4 — don't accidentally revert. Also: session_active_seconds is exposed via ProjectService and tausik_status MCP JSON for sub-minute precision; agents that aggregate over short bursts should prefer it over active_minutes.
