**English** | [Русский](../ru/sessions.md)

# A "session" is TWO things

<!-- doc-map: reader=user; zone=sessions -->

Decision #223. The word "session" in TAUSIK fuses two concepts with different
fates, and the fusion is precisely what made it impossible to answer which of
them could be dropped.

| | What it is | A property of |
|---|---|---|
| **Work continuity** | handoff: what was done, what is in flight, what comes next, what to warn about | a property of the **WORK** |
| **Agent context hygiene** | the session's active time, the call capacity, the checkpoint counter — since 1.10 **signals, not gates**: they advise a checkpoint or a handoff and never refuse a task start | a property of the agent's **CONTEXT WINDOW** |

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

Since 1.10 the absence of a session is an **explicitly named state, not a
refusal** (decision #376: capacity is a signal, not a gate). A task that
declared a budget starts, and an advisory line in the `task start` output says
that capacity is unmeasured and names `tausik session start`. There is no
refusal in either case — neither without a session nor when the budget exceeds
what remains: measured over 70 sessions (#196–#265), the capacity gate was
what cut sessions short and drove restarts, and it was never a Quality Gate —
it has no declared prevented effect (SENAR 1.5 §8.6(a)). A task without a
budget gets no advice either: the signal has an opinion only about what asked
to be accounted for.

### What else silently switches off without an open session

This matters because every mechanism below fails by **writing a zero**, not an
error — the only way to notice the loss was an empty report:

| Mechanism | What happens |
|---|---|
| Usage telemetry (`posttool_usage`) | no rows written at all ⇒ `tasks.cost_actual_usd` and `tokens_actual` stay zero for **every** task, and the cost budget never fires |
| Token metrics | `.tausik/token_metrics.jsonl` stops growing; `tausik metrics tokens` prints "no data yet" |
| Model pinning | `started_model_id` / `done_model_id` stay NULL, `model_mismatch` never fires again |
| The brain's "this session" slice | computed over all time and **passes itself off as per-session** — not empty but wrong; the most dangerous case in this list |
| ~~Audit cadence (SENAR 9.5)~~ | **LEFT in 1.10**: the clock is task closures since the last mark (`audit_every_closures`, default 17 = 3 sessions × 5.72 tasks/session); no session needed |

That is why the capacity advisory names `tausik session start` — one action
restores everything above.

#### Usage telemetry has LEFT this list (schema v48)

It stood here not by design but because `usage_events.session_id` was declared
`NOT NULL`: an event belonging to a TASK but not to a session had nowhere to go,
and the hook dropped it whole — while `task_slug` was already known at that
moment. Attribution had been keyed on the wrong thing all along: the target is
the task, which is what carries `cost_actual_usd`, `tokens_actual` and
`started_model_id`.

`session_id` is now optional, and work without an open session is **recorded in
full**: the row gets a live `task_slug` and `session_id=NULL`. An event with
neither a task nor a session does not vanish either — it lands in an explicit
"outside a task" bucket and is printed by `tausik metrics cost` (including when
the per-task table is empty). Otherwise a silent drop on write would simply have
become a silent omission on read.

The other four rows of the table stand: a session is still needed for token
metrics, model pinning, the brain slice and the audit cadence.

## The session is the host session (1.10)

Decision #376. Until 1.10 `/start` opened a session and `/end` closed it — a
ritual an autonomous agent does not perform: session #265 stayed open nine days
at 76 active minutes. Now the unit "session" is the host session:

- **The SessionStart hook** opens a TAUSIK session keyed by the `session_id` in
  the host's payload (`session start --host-id <id>`). Opening is idempotent:
  SessionStart firing again after a resume or a compaction with the same id
  does not create a second row.
- **The SessionEnd hook** first records the transcript's metrics into this
  host's session, then closes exactly that session (`session end --host-id
  <id>`). The order inside one process is deliberate: Claude Code runs the hooks
  of one event in parallel, and a separate closing hook could beat the metrics.
- **Two host sessions are two TAUSIK sessions.** Closing one does not touch the
  other; `session end --host-id` with an unknown id closes nothing.
- **Without a host id** (CLI, MCP, hosts without session events — Codex,
  OpenCode, Kilo) the old contract holds: one open session, `session start` /
  `session end` by hand. Which host gives which events is the task
  `session-ceremonies-are-hooks-on-every-host-or-an-honest-gap`.

**The handoff is generated from the journal.** `session handoff` without
arguments (and `tausik_session_handoff`) builds the document from the records
of the session's window: completed tasks, active tasks with their last log
line, verify receipts, decisions, memory, dead ends, the open exploration.
Authored `next_steps`, `warnings` and `in_progress[].state` land on top and are
listed in `authored_fields`; a field the generator produces itself (such as
`completed`) stays with the records, and the authored version is kept beside it
under `authored`. A task is called completed only when its status is `done`; a
window with no records says so in words. `session end` writes the generated
handoff itself when none was written in the session; a failing generator does
not stop the end and leaves a `handoff_generate_failed` event.

**The checkpoint counter is derived, not maintained (1.10).** Calls since the
last checkpoint are the session's rows in `usage_events` minus the
`calls_at_write` its last handoff recorded. There is no counter field any more;
only the ten-call bucket already warned about is stored. Without an open
session the count is named unmeasured, not zero.

**Journal freshness is a signal (1.10).** When an active task has gathered
40 or more calls since its last `task log` entry (`journal_freshness.py`;
basis: session #266 measured a median gap of 0, p90 of 2, 1.4% of gaps at 40
or more), the MCP response carries advice to record the step. It counts per
task, so it works with no session. It does not block closing the task.

**One live handoff.** With two host sessions, "the highest session number"
stops meaning "written last". A handoff carries `written_at` (with
microseconds) and `supersedes` — the session whose handoff it took over from;
the live one is the one written last. The previous one is not deleted and is
read with `session last-handoff --session N`.

Schema v63 adds `sessions.host_session_id`; old rows keep NULL and work with
every consumer.

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
