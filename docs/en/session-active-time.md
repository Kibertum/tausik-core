**English** | [Русский](../ru/session-active-time.md)

# Session Active Time (v1.4)

<!-- doc-map: reader=user; zone=sessions -->

SENAR Foundation (10.2) requires a documented maximum session duration with a basis; SENAR Core, the edition TAUSIK claims, does not govern sessions at all. In TAUSIK the **180-minute** threshold is, since 1.10, **advice, not a gate** (decision #376): above it `task start`, `status` and the Stop hook print a warning and refuse nothing. The threshold is measured on **active time**, not wall-clock — long pauses are clipped to the idle threshold instead of being dropped entirely. This page explains the algorithm, the semantics choice (clip vs exclude), the basis of the threshold, and how to tune it.

## Why Active Time

Wall clock punishes natural breaks. A session that starts at 09:00, pauses for an hour-long meeting, and resumes at 11:00 would hit "120 min" without the agent doing 120 min of work. v1.3+ fixes that by computing **gap-based active time**: a bounded sum of inter-tool-call intervals.

## Algorithm

Every call of a tool the hook is registered for — writes, the shell, reads, search, web and the external MCP write tools, the same set on every host since 1.10 — writes a row to `events` (via the `activity_event.py` PostToolUse hook). Active time is the **bounded** sum of intervals between consecutive timestamps:

```
active_seconds = Σ min(t[i+1] − t[i], idle_threshold_seconds)
```

Each gap is clipped at `idle_threshold` (default **600 s / 10 min**). A long AFK gap (e.g. three hours) contributes exactly the threshold to active — enough to credit "the agent worked right before pausing", but not enough to give a multi-day session for free against the Rule 9.2 budget.

```
events:    t1   t2   t3 ---(huge gap)--- t4   t5
intervals: Δ1   Δ2   Δ3(clipped→10m)     Δ4
active     = Δ1 + Δ2 + 10m + Δ4
wall       = t5 − t1
```

**v1.4 polish (v14b-session-active-time)** flipped the semantics from "exclude" (gap ≥ threshold → 0) to "clip" (gap ≥ threshold → threshold). Clip is more conservative: a long AFK still spends ~10 min against the limit, so an agent can't run a multi-day session for free.

## Threshold Configuration

`.tausik/config.json`:

```json
{
  "session_idle_threshold_minutes": 10,
  "session_max_minutes": 180,
  "session_warn_threshold_minutes": 150,
  "session_capacity_calls": 200
}
```

| Knob | Default | Meaning |
|------|---------|---------|
| `session_idle_threshold_minutes` | 10 | Gaps above this clip to the threshold (each long AFK contributes exactly this much to active time, not zero) |
| `session_max_minutes` | 180 | Advisory threshold — above it `task_start`, `status` and the Stop hook print a warning, not a refusal (`session extend` raises it) |
| `session_warn_threshold_minutes` | 150 | Soft warning starts here |
| `session_capacity_calls` | 200 | Capacity in **tool calls**, not minutes; a task budget above what remains is an advisory line in the `task_start` output, not a refusal |

## Where You See It

`tausik status` shows both numbers when a session is open:

```
Session: 76m active / 145m wall
```

`tausik doctor` echoes the same.

## Retro Computation

If you tune the idle threshold or want to see how a past session looked under a different setting, run:

```bash
.tausik/tausik session recompute
```

This re-walks `session_activity` events for past sessions and prints `wall vs active` per session. The recompute is read-only — it does not mutate the stored values unless you pass `--write` (where supported).

## Activity Hook

`scripts/hooks/activity_event.py` is the PostToolUse hook that stamps `(session_id, tool_name, timestamp)` into `session_activity`. It runs on the tools named in its matcher, identical for Claude, Qwen and Codex. Disable with `TAUSIK_SKIP_HOOKS=1` only for debugging — disabling it makes active time stop accumulating until re-enabled.

## Override / Extend

If you legitimately need a longer session (e.g. release day):

```bash
.tausik/tausik session extend --minutes 60
```

`task_start --force` was retired in 1.10: capacity is no longer a gate, so there is nothing to bypass; the flag is refused with the reason (decision #376).

## The basis of the threshold (SENAR 1.5 §9.4(c))

The numbers 180 / 150 / 200 are inherited from the SENAR 1.3 §9.2 guideline ("sessions exceeding 180 minutes show diminishing returns") and held a gate until 1.10. Session #266 measured 70 sessions #196–#265 (`tausik session recompute --limit 70`): one crossed 180 active minutes (#241, 246 minutes, with no extension), the median is 73, p90 146; `session extend` was never called, and the summaries of 13 sessions name capacity as the reason they stopped. That is why the threshold became advice. The basis is recomputed by a command: `session recompute` prints a `SUMMARY` line — median, p90 and maximum active minutes and how many sessions sit above the threshold (on 2026-09-23 over sessions #196–#265: median 73, p90 146, above 180: 1). Crossing the threshold is recorded as a `session_threshold_crossed` event once per session (§9.4(d)). Every threshold — `session_max_minutes`, `session_capacity_calls`, `checkpoint_calls` (40), `journal_freshness_calls` (40) — is switched off by 0.

## Negative — What Active Time Is Not

- It is **not** wall clock — long pauses are dropped above the idle threshold.
- It is **not** an estimate of real focused-work time. Tool calls are the proxy; if you read code in your head without tool use, the timer pauses.
- The **180** threshold is on **active**, not wall. A session that has been open for 12 hours with 30 min of activity is still at 30 min and well under the threshold.
- It is **not** a gate: crossing the threshold prints advice and refuses nothing (1.10, decision #376).

## What's Next

- **[Configuration](configuration.md)** — full list of knobs in `.tausik/config.json`
- **[CLI Commands](cli.md)** — `session start/extend/recompute` reference
- **[Hooks](hooks.md)** — the activity hook and other PostToolUse hooks
