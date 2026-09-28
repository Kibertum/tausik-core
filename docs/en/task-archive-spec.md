**English** | [Русский](../ru/task-archive-spec.md)

# Soft-archive of old **done** tasks (hygiene)

<!-- doc-map: reader=user; zone=sessions -->

Hide stale completed tasks from `task list` without losing them. Active work is never affected.

## Goal

Keep the working set focused: stamp `archived_at` on **done** tasks whose `completed_at` is older than **N** days. They stay in the database (so audits, FTS, `task show` keep working) but disappear from `task list` by default.

## Config (`.tausik/config.json`)

```json
{
  "task_archive": {
    "enabled": false,
    "done_age_days": 90,
    "note": "soft-delete only; status stays 'done', archived_at is the marker"
  }
}
```

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `task_archive` | object | (absent) | Entire feature off when missing or `enabled: false`. |
| `enabled` | bool | `false` | Required to be `true` for `hygiene archive --confirm` to do any writes. |
| `done_age_days` | int | `90` | Only tasks with `status = 'done'` and `completed_at ≤ now − N days` are in scope. Invalid/0 clamps to `1`. |

`enabled: false` overrides `--confirm` — the command prints a "disabled" notice and writes nothing.

## Inclusion rules (positive)

- `task.status == 'done'`
- `task.completed_at` present and **older** than `done_age_days` (UTC comparison).
- `task.archived_at IS NULL` (already-archived rows are skipped — `--confirm` is idempotent).

## Negative rules (hard)

- **Never** include `planning`, `active`, `blocked`, or `review` tasks — no matter what the age or config says.
- **No row deletion**: archive is a soft-delete (`UPDATE ... SET archived_at = ?`). The `tasks` row, its FTS index, logs, decisions, and metrics participation all remain intact.

## CLI

```bash
tausik hygiene archive             # dry-run: list candidates
tausik hygiene archive --confirm   # apply: stamp archived_at on candidates (idempotent)

tausik hygiene unarchive --slug <slug>              # dry-run: what this would unhide
tausik hygiene unarchive --slug <slug> --confirm    # apply: clear archived_at
tausik hygiene unarchive --archived-within 1 --confirm   # undo a batch archived today

tausik task list                       # default: hides archived rows
tausik task list --include-archived    # opt-in: shows everything
```

`tausik_task_list` MCP tool accepts the same `include_archived: bool` parameter.

## Reversal

`hygiene unarchive` clears `archived_at`. **It is the only path that does** — for two
releases this section promised reversibility "by command" while no such command existed,
so recovering a batch would have required raw SQL, which this project forbids. The claim
now names the command, and `tests/test_hygiene_unarchive.py` asserts the command exists:
a promise of reversal is only worth reading if something checks it.

Rules:

- **A selector is required**: `--slug` or `--archived-within DAYS`. A bare `unarchive`
  would unhide the whole archive, which is not a recovery.
- **`--archived-within`, not "older than"**: what needs undoing is the batch somebody
  just ran. Selecting the oldest archived rows would restore exactly what was meant to
  stay hidden and leave the fresh mistake in place.
- **Only `archived_at` and `updated_at` move.** `status` and `completed_at` are left as
  they were — archiving never changed them, so lifting the flag unhides the row rather
  than reviving the work.
- **Not gated on `task_archive.enabled`.** The config gates the operation that hides
  rows; a recovery path that switched off with it would be unavailable exactly when it is
  needed.

### Memory archival is not reversible, and that is deliberate

Archiving a **memory** row stamps `valid_to` on its graph edges
(`backend_graph.edges_invalidate_to`). Clearing the flag would not bring the edges back,
so there is no `memory unarchive` and the asymmetry is on purpose rather than an omission.
A task carries no such edges: unhiding one loses nothing.

## Schema

Migration v25 adds a single nullable column:

```sql
ALTER TABLE tasks ADD COLUMN archived_at TEXT;  -- ISO8601 UTC timestamp
CREATE INDEX idx_tasks_archived_at ON tasks(archived_at);
```

## See also

- [Testing principles](testing-principles.md) — scoped changes and evidence.
- [CLI — Tasks](cli.md#tasks) — current task commands.
