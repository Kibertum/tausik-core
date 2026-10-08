---
slug: hook-wall-clock-tax-nothing-to-do-in-1-10-measured-session
task: hook-wall-clock-tax-per-bash-call-is-unmeasured
date: "2026-09-23"
edges: []
---

## Decision

HOOK WALL-CLOCK TAX — NOTHING TO DO IN 1.10 (measured, session #269). The harness runs the hooks matched by one tool call in PARALLEL (process creation timestamps: 5 PreToolUse interpreters within 14 ms, 6 PostToolUse within 12 ms), so the cost is max(pre)+max(post) ~ 55+67 = ~120 ms per Bash call, not the 578 ms sum filed in session #229. Floor is the 22 ms interpreter; the whole headroom is ~78 ms/call, ~13 min over 9844 calls. Revisit only if one hook's median exceeds ~150 ms: then it alone sets the max.

## Rationale
