---
slug: gate-b-keep-sub-agents-tausik-reviewer-tausik-gate-fixer-in
task: null
date: "2026-05-07"
edges: []
---

## Decision

Gate B: KEEP sub-agents (tausik-reviewer + tausik-gate-fixer) in v1.4.0. Quantitative token-reduction remeasure DEFERRED to post-1.4 telemetry sweep — current token_metrics.jsonl has insufficient post-sub-agent sample sessions (need ≥10) for valid baseline comparison.</decision>
<parameter name="task_slug">v14b-post-subagent-remeasure

## Rationale

**Why KEEP now (qualitative):** (1) Both sub-agents landed and operate correctly per their own AC suites — `tausik-reviewer` smoke caught planted SQLi + cleartext-token logging; `tausik-gate-fixer` returned valid 1-3 step JSON plans on synthetic ruff E501 stderr. (2) /review Lite mode is opt-in (`/review lite`) — default 6-agent flow unchanged, so users who don't use Lite see zero impact; reverting now would remove value already validated by other tasks. (3) Sub-agent .md definitions are <3KB each (read-time, not embedded), so the cost of carrying them forward is negligible.

**Why DEFER quantitative measure:** Per task notes, the remeasure is intentionally not closable in a single session — it requires ≥10 real sample sessions exercising /review + /debug + verify flows with sub-agents enabled to populate token_metrics.jsonl with valid post-baseline data. We have telemetry from session #71 (this one) and a handful of sessions since #67 when sub-agents landed; that's <10. Forcing a quantitative decision now would either fabricate numbers or block 1.4 closure on a multi-session-time-window dependency. Spawning a follow-up task `v14b-followup-subagent-remeasure-quant` for post-1.4 sweep — when ≥10 sessions have accumulated, run `tausik metrics tokens`, compute reduction %, record as second tausik_decide (and revert sub-agents in 1.4.x patch if reduction <15%).

**Threshold semantics:** Original AC-3 said "keep ≥15% input-token reduction; revert if <15%". KEEP-pending-remeasure means: presumption of keeping unless post-1.4 quantitative shows clear regression. This is the conservative path — sub-agent code is already in main, reverting would be more disruptive than waiting one telemetry cycle.

**Rollback contract preserved:** AC-4 rollback recipe (.claude/agents/*.md removal + /review revert to inline) remains valid for post-1.4 1.4.x patch if needed; nothing in 1.4 closure makes the revert harder.
