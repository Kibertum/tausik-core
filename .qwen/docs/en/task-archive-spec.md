**English** | [Русский](../ru/task-archive-spec.md)

# Specification: read-only archive of old **done** tasks (hygiene)

**Status:** design / future implementation — no CLI or DB migration ships with this document alone. Use this spec when implementing `hygiene` automation (see project hygiene epic).

## Goal

Surface **read-only** visibility into **done** tasks whose `completed_at` is older than **N** days (audits, storage planning). **Active work must never be affected.**

## Config (`.tausik/config.json`)

Proposed optional block (ignored by current releases until implemented):

```json
{
  "task_archive": {
    "enabled": false,
    "done_age_days": 90,
    "note": "read-only; never mutates non-done tasks"
  }
}
```

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `task_archive` | object | (absent) | Entire feature off when missing or `enabled: false`. |
| `enabled` | bool | `false` | When `true`, tooling may list/export archived *candidates* (done + older than threshold). |
| `done_age_days` | int | `90` | Only tasks with `status = done` and `completed_at` ≤ *now − N days* are in scope. |

Invalid/missing `done_age_days` → implementation should treat as “feature off” or clamp to a safe minimum (e.g. ≥1), **documented in the implementation PR**.

## Inclusion rules (positive)

- `task.status == 'done'`
- `task.completed_at` present and **older** than `done_age_days` (UTC comparison).

## Negative rules (hard)

- **Never** include `planning`, `active`, `blocked`, or `review` tasks — **no matter what** the age or config says.
- **No destructive writes** in v1 of this spec: no auto-delete, no auto-move to another table, without a separate feature flag and user confirmation (out of scope here).

## Suggested future CLI (non-normative)

`tausik hygiene archive list --dry-run` — print slugs that *would* match; requires `task_archive.enabled` in a future release.

## See also

- [Testing principles](testing-principles.md) — scoped changes and evidence.
- [CLI — Tasks](cli.md#tasks) — current task commands.
