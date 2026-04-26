**English** | [Русский](../ru/session-active-time.md)

# Session Active Time (v1.3)

SENAR Rule 9.2 limits a session to **180 minutes**. In v1.3 that 180 is **active time**, not wall-clock — paused intervals are not counted. This page explains how active time is measured, why it changed, and how to tune the threshold.

## Why Active Time

Wall clock punishes natural breaks. A session that starts at 09:00, pauses for an hour-long meeting, and resumes at 11:00 would hit "120 min" without the agent doing 120 min of work. v1.3 fixes that by computing **gap-based active time**: time the agent was actually doing things.

## Algorithm

Every tool call writes a row to `session_activity` (via the `activity_event.py` PostToolUse hook). Active time is the sum of intervals between consecutive activity timestamps where the gap is **below the idle threshold**.

```
events:    t1   t2   t3 ----- (gap ≥ idle) ----- t4   t5
intervals: [t1..t2] + [t2..t3] + [t4..t5]
active     = sum of those intervals
wall       = last_event - first_event
```

If the gap between two consecutive events is ≥ `session_idle_threshold_minutes` (default **10 min**), the gap is treated as **AFK** and dropped from the sum.

## Threshold Configuration

`.tausik/config.json`:

```json
{
  "session_idle_threshold_minutes": 10,
  "session_max_minutes": 180,
  "session_warn_threshold_minutes": 150,
  "session_capacity_minutes": 200
}
```

| Knob | Default | Meaning |
|------|---------|---------|
| `session_idle_threshold_minutes` | 10 | Gap above this is AFK and drops from active time |
| `session_max_minutes` | 180 | Hard limit — `task_start` blocks above this (`session extend` to override) |
| `session_warn_threshold_minutes` | 150 | Soft warning starts here |
| `session_capacity_minutes` | 200 | Capacity gate that QG-0 evaluates on `task_start` |

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

`scripts/hooks/activity_event.py` is the PostToolUse hook that stamps `(session_id, tool_name, timestamp)` into `session_activity`. It runs on every tool call. Disable with `TAUSIK_SKIP_HOOKS=1` only for debugging — disabling it makes active time stop accumulating until re-enabled.

## Override / Extend

If you legitimately need a longer session (e.g. release day):

```bash
.tausik/tausik session extend --minutes 60
```

`task_start --force` is a separate escape hatch that bypasses the **capacity gate** with an audit-event trail; it is not a substitute for `session extend`.

## Negative — What Active Time Is Not

- It is **not** wall clock — long pauses are dropped above the idle threshold.
- It is **not** an estimate of real focused-work time. Tool calls are the proxy; if you read code in your head without tool use, the timer pauses.
- The **180** limit is on **active**, not wall. A session that has been open for 12 hours with 30 min of activity is still at 30 min and well under the limit.

## What's Next

- **[Configuration](configuration.md)** — full list of knobs in `.tausik/config.json`
- **[CLI Commands](cli.md)** — `session start/extend/recompute` reference
- **[Hooks](hooks.md)** — the activity hook and other PostToolUse hooks
