---
slug: session-duration-fix
title: "Session active-time (gap-based) instead of wall-clock"
status: done
epic: v13-mcp-and-discipline
---

Replace wall-clock session duration with sum-of-active-intervals computed from events table. AFK gaps >10 min excluded. Show both numbers in `tausik status`. Retro-recompute past 36 sessions for real SENAR throughput.
