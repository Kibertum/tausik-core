# A "session" is TWO things

Decision #223. The word "session" in TAUSIK fuses two concepts with different
fates, and the fusion is precisely what made it impossible to answer which of
them could be dropped.

| | What it is | A property of |
|---|---|---|
| **Work continuity** | handoff: what was done, what is in flight, what comes next, what to warn about | a property of the **WORK** |
| **Agent context hygiene** | the 180 active-minute limit (SENAR 9.2), the 200-call capacity, the checkpoint counter (SENAR 9.3) | a property of the agent's **CONTEXT WINDOW** |

The two halves are no longer coupled. They used to be, in three ways, and every
one of them looked harmless:

- `session_handoff` refused when the window was closed. It is the other way
  round: an agent that has hit the 180-minute limit is exactly the one who most
  needs to write down where it stopped. The refusal destroyed the very document
  the limit exists for.
- Saving a handoff zeroed `tool_call_count`. Resetting the counter is hygiene,
  and it is now a separate named operation, `reset_checkpoint_counter`, rather
  than a side effect of writing a document. `/checkpoint` still does both — but
  explicitly, and in that order.
- The capacity gate silently waved everything through when no session was open.
  See below.

## Why continuity was NOT dropped

The task this split grew out of proposed discarding the first half: its role,
the argument went, had been taken over by the git projection. That premise was
**refuted by measurement**, not by opinion — four facts:

1. **The projection is off by default.** `state.auto_export` has no default
   anywhere: `DEFAULT_CONFIG` carries no `state` key at bootstrap, and the
   resolver returns `False` on any error. A fresh project has no projection.
2. **Sessions are not projected at all.** `ENTITY_DIRS = (epics, stories, tasks,
   decisions, memory)`. Even with the projection **enabled**, a handoff never
   reaches the tree.
3. **The handoff fields have no other home.** The tree carries "what changed" —
   task status, its log, decisions, memory. `next_steps`, `warnings` and
   `in_progress[].state` ("step 3 of 5") have a column nowhere except
   `sessions.handoff`.
4. **The projection calls itself incomplete.** Its docstring enumerates what it
   does not cover by name, coverage rests on ~18 manual call sites, and every
   trigger is fail-open.

**The condition for a future drop is named explicitly:** the handoff must gain a
projected home, i.e. `sessions` must enter `ENTITY_DIRS`. The condition is
checked by `tests/test_session_two_halves.py::TestTheDropConditionIsNotMet` — if
it goes red, that is not a regression but a signal to revisit #223.

What was refuted **in the task's favour**: calibration does not depend on
sessions at all. `calibration_drift` and `per_tier_metrics` read only the `tasks`
table (`call_budget`/`call_actual`/`tier`/`completed_at`), without a single join
to `sessions`.

## No session is NOT "unlimited"

The capacity gate used to return early when no session was open: the 200-call
check stopped checking and said nothing about it. Worse, it inverted the
incentive — the cheapest way to get around a capacity refusal was to end the
session and not start a new one.

Now the absence of a session is an **explicit refusal** for a task that declared
a budget. A task without a budget starts as before: the gate has an opinion only
about what asked to be accounted for.

### What else silently switches off without an open session

This matters because every mechanism below fails by **writing a zero**, not an
error — the only way to notice the loss was an empty report:

| Mechanism | What happens |
|---|---|
| Usage telemetry (`posttool_usage`) | no rows written at all ⇒ `tasks.cost_actual_usd` and `tokens_actual` stay zero for **every** task, and the cost budget never fires |
| Token metrics | `.tausik/token_metrics.jsonl` stops growing; `tausik metrics tokens` prints "no data yet" |
| Model pinning | `started_model_id` / `done_model_id` stay NULL, `model_mismatch` never fires again |
| The brain's "this session" slice | computed over all time and **passes itself off as per-session** — not empty but wrong; the most dangerous case in this list |
| Audit cadence (SENAR 9.5) | "3 sessions since the last audit" never arrives |

That is why the capacity gate's refusal names `tausik session start` — one
action restores everything above.

## What did not change

The `sessions` table, `session_start`/`session_end`, handoffs, and the metrics
that slice by session (`throughput` as "tasks per session", `session_hours`, the
token-metrics window "last N sessions", audit cadence). The split removed the
coupling, not the data.

## See also

- [team-state-in-git.md](team-state-in-git.md) — the git projection and its flag.
- [../ru/agent-contract.md](../ru/agent-contract.md) — SENAR rules 9.2/9.3/9.5
  (Russian only; no English mirror exists yet).
- [cost-telemetry.md](cost-telemetry.md) — what usage telemetry actually writes.
