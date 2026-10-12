[Русский](../ru/state-projection-cost.md) | **English**

# What the state projection costs, and why every kind stays

<!-- doc-map: reader=maintainer; zone=reference -->

The `tausik/` Markdown tree is 68.6% of this repository's tracked paths. This page says what
that buys, what it costs, and what was decided about each kind — measured, because the story
that asked the question had guessed wrong twice.

Re-measure at any time:

```bash
python scripts/projection_census.py --db .tausik/tausik.db
```

## The measurement

| Kind | Files | Bytes | Avg | Share of tree bytes |
|---|---:|---:|---:|---:|
| `tasks` | 1744 | 11,933,248 | 6,842 | 39.1% |
| `memory` | 765 | 1,465,331 | 1,915 | 4.8% |
| `decisions` | 401 | 655,171 | 1,633 | 2.1% |
| `stories` | 297 | 102,467 | 345 | 0.3% |
| `epics` | 109 | 36,786 | 337 | 0.1% |
| `graph-snapshots` | 1 | 157,751 | 157,751 | 0.5% |
| **projection** | **3317** | **14,350,754** | | **47.1%** |
| tracked tree | 4832 | 30,484,187 | | 100% |

Two more numbers from the same tree:

* **Journals are 47.8% of task-file bytes** (5.7 MB). The rest is front matter, goal and
  acceptance criteria — a row's shape. The journal is the part a writing habit moves.
* **Over the whole history, the projection is 48.7% of file-touches but 14.8% of line
  churn.** It is rewritten constantly and changes little each time.

## What the guess got wrong

The hygiene story planned on soft-archiving old done tasks to cut a projection "occupying
69% of the tree". Both halves were wrong.

1. **Archival does not touch the projection.** `state_export` selects `FROM tasks` with no
   `archived_at` filter. Archiving hides a task from `task list`; the file stays.
2. **The reachable ceiling is 19%, not 69%.** 917 task files match "done and older than 90
   days" — 2.7 MB, 19.0% of tracked paths. Even a filter that removed all of them would
   leave the projection at half the tree.

## Why removing them is not on the table

**`.tausik/tausik.db` is gitignored.** The Markdown tree is the only carrier of state
between machines: a row dropped from the tree is a row a fresh clone never sees. Hiding a
task from a listing and deleting its record are different acts, and archival was built for
the first. `tests/test_projection_census.py::TestTheTreeIsTheOnlyCarrier` pins both facts —
if the database ever starts travelling, this decision has to be retaken rather than
inherited.

## The verdict, per kind

| Kind | Verdict | Why |
|---|---|---|
| `tasks` | **stays** | The tree is the only carrier; dropping archived rows would lose 917 tasks on a fresh clone. The journal is the evidence a closure happened, which is the record SENAR asks for. |
| `memory` | **stays** | Same carrier argument. It already filters `archived_at IS NULL` on export, so what is hidden is hidden and what is kept travels. |
| `decisions` | **stays** | 2.1% of the tree and the thing most often read by a fresh agent. Nothing to win. |
| `stories` | **stays** | 0.3% of bytes. Removing it would cost more in review than it saves in checkout. |
| `epics` | **stays** | 0.1% of bytes. Same. |
| `graph-snapshots` | **stays** | One gzipped file per release, kept on purpose as a before-picture. It is the largest single file in the projection and still half a percent of the tree. |

## The lever that does exist

Growth is bounded at the point of writing, not by deletion: the journal budget advises on
every `task log` entry, and journals are where 47.8% of the task bytes are. That is a habit
with a brake on it, which is a different mechanism from a threshold on the total.

**There is deliberately no ratchet on the projection's share.** Every closed task adds a
file, so a threshold on the total would be crossed by ordinary work — and a threshold
ordinary work crosses is one somebody switches off, taking the measurement with it. The
census reports; it never fails a build.

## See also

- [Task archive spec](task-archive-spec.md) — what archival does and does not do, and the
  one command back.
- [Architecture](architecture.md) — where the exporter sits.
