# TAUSIK state in git — contract (team-state-in-git)

> Format spec for the git-native projection of project state. Depended on by
> `state-git-stable-ids`, `state-git-export`, `state-git-import`,
> `state-git-triggers`, `state-git-roundtrip-gate`. Decision `#172`.

## Why

All of `.tausik/` is `.gitignore`d and `tausik.db` is a binary SQLite file: a
teammate who `git clone`s sees no tasks, decisions, or project memory, and two
edits into one DB cannot merge. The state is also **branch-blind** — switching
branches does not change `.tausik/`.

Decision (`#172`): durable project state travels as **git-native text files in
the branch**, one file per entity. Git is the canonical source of truth; the DB
is a rebuildable working cache. Merging state = `git merge` of branches: a
decision made on `feature-A` arrives in `main` exactly when `feature-A`'s code
does. An external store (Notion/server) is unfit for this — it is
branch-agnostic and decouples state from code.

Two tiers. **Tier 1 (this spec):** durable, code-coupled. **Tier 2
(deferred):** live "who is on what right now, before merge" awareness — not
covered here.

## What travels in git, what does not

The projection is **durable intent and outcome**, not runtime telemetry. Rule:
travels what is meaningful to read in a colleague's PR; does not travel what is
bound to a specific machine/run and goes stale fast.

| Table | In git? | Why |
|---|---|---|
| `tasks` | **yes** (field subset, see below) | core: what is being done, goals, AC, plan |
| `task_logs` | **yes** | progress journal — append-only, merges as added lines |
| `epics` | **yes** | work structure |
| `stories` | **yes** | work structure |
| `decisions` | **yes** | project architectural decisions |
| `memory` | **yes** | patterns/gotchas/conventions of THIS project |
| `memory_edges` | **yes** | memory/decision link graph |
| `task_specs` | **yes** | task-to-spec links |
| `specs` | **yes** | project specifications |
| `verification_runs` | no | proof of a run on a SPECIFIC machine; signatures bound to a local key; goes stale fast |
| `gate_runs` | no | gate-run telemetry |
| `reviews` | no | bound to a run/reviewer |
| `sessions` | no | ephemeral: who sat when |
| `session_usage_metrics` | no | telemetry |
| `usage_events` | no | telemetry |
| `events`, `events_anchor` | no | local audit hash-chain; unmergeable by construction |
| `reasoning_steps` | no (v1) | RENAR trace; tier-2 candidate, local for now |
| `explorations` | no | ephemeral investigation time-boxes |
| `roles`, `adapts*`, `snippets`, `brain_events`, `meta`, `sync_state` | no | config/runtime/cross-project, not team state |

### `tasks` fields — durable vs runtime

Travels (intent and outcome): `slug`, `title`, `status`, `stack`,
`complexity`, `role`, `tier`, `goal`, `plan`, `acceptance_criteria`,
`rollback_plan`, `scope`, `scope_exclude`, `scope_paths`, `scope_tools`,
`relevant_files`, `defect_of`, `call_budget`, `completed_at`, story link.

Does NOT travel (local runtime/telemetry): `id`, `score`, `attempts`,
`claimed_by`, `call_actual`, `cost_budget_usd`, `cost_actual_usd`,
`token_budget`, `tokens_actual`, `risk_score`, `risk_json`,
`started_model_id`, `started_model_version`, `done_model_id`,
`done_model_version`, `model_mismatch`, `no_file_changes_declared`,
`started_at`, `blocked_at`, `created_at`, `updated_at`, `archived_at`.
`notes` does not travel as its own field — the journal is `task_logs`.

## Directory layout

The projection root is `tausik/` at the repo root (NOT `.tausik/`, which stays
private and ignored). One file per entity:

```
tausik/
  epics/<epic-slug>.md
  stories/<story-slug>.md
  tasks/<task-slug>.md
  decisions/<decision-slug>.md
  memory/<memory-slug>.md
  specs/<spec-slug>.md
```

One file per entity — so two engineers' edits on different tasks merge cleanly
and a conflict localises to one file. The file name is the entity's **stable
slug** (not the local `id`).

## File format

Markdown + YAML frontmatter. **Frontmatter is machine fields** (identity,
status, links, enumerations). **Body is prose** (goal, AC, plan, journal,
content). This split lets Obsidian open the files as a vault and a human read
the diff.

### Task — `tausik/tasks/<slug>.md`

```markdown
---
slug: state-git-export
title: "Export DB -> git-native files"
status: planning
epic: team-state-in-git
story: state-in-branch-mvp
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
relevant_files:
  - scripts/state_export.py
  - tests/test_state_export.py
scope_paths:
  - scripts/state_*.py
  - tests/*
completed_at: null
---

## Goal

<goal text>

## Acceptance Criteria

<acceptance_criteria text>

## Plan

<plan text>

## Rollback

<rollback_plan text>

## Journal

- 2026-07-24T15:00:00Z — first log message
- 2026-07-24T15:20:00Z [verify] — message with a phase
```

`Journal` is the projection of `task_logs`, **append-only**: new entries are
only appended at the end. Line format: `- <created_at> [<phase>] — <message>`
(the `[<phase>]` segment is dropped when phase is empty). This way the journal
of two branches merges as added lines, nearly conflict-free.

### Decision — `tausik/decisions/<slug>.md`

`decisions` has neither slug nor title in the DB. The stable slug is generated
in `state-git-stable-ids` (deterministically from content+date). The first line
of `decision` serves as the heading.

```markdown
---
slug: state-in-branch-over-external-store
task: state-git-spec
date: 2026-07-24
---

## Decision

<decision text>

## Rationale

<rationale text>
```

### Memory — `tausik/memory/<slug>.md`

The slug is derived from `title` (kebab-case, stabilised in
`state-git-stable-ids`).

```markdown
---
slug: state-decoupled-from-code-lies
type: convention
tags:
  - git
  - team
  - state
task: state-git-spec
edges:
  - relation: relates_to
    target_type: decision
    target: state-in-branch-over-external-store
---

<content text>
```

`edges` is the projection of `memory_edges` where this entry is the source.
`target` is the **stable slug** of the target entity, not an integer `id`.

### Epic / story / spec

`epics/<slug>.md` and `stories/<slug>.md` — frontmatter (`slug`, `title`,
`status`; story also has `epic`) plus a `description` body. `specs/<slug>.md` is
analogous, with the spec body and `task_specs` links in frontmatter.

## Round-trip contract (normalisation)

`export(DB)` -> files and `import(files)` -> DB must be **mutually inverse**. So
that the same state yields a **byte-identical** file on any machine and on
re-export (else diffs get noisy and merges falsely conflict), the serialiser
must:

1. **Newlines are LF only** (`\n`), including on Windows. Exactly one trailing
   `\n`.
2. **Frontmatter key order is fixed**, set by this spec (not by DB column or
   insertion order). The order list is part of the contract.
3. **Lists sort deterministically**: `tags` alphabetically; `relevant_files`,
   `scope_paths` keep the user's declared order (it is significant — the
   ordering convention) but drop duplicates. `edges` sort by the tuple
   `(relation, target_type, target)`.
4. **Dates are ISO-8601 UTC** with a `Z` suffix, no microseconds.
5. **Empty/`null` fields** are serialised explicitly (`field: null`), not
   omitted — so a missing field and an empty one are not confused on import.
6. **YAML with no anchors, flow style, or smart types**: strings YAML could read
   as a number/date/bool (a slug `2026-01`, a status `on`) are quoted.
   Multi-line prose lives in the body, not frontmatter.

Property for the gate (`state-git-roundtrip-gate`): `export(current_db)` yields
files **byte-equal** to those in git; and `import(export(db))` yields a DB
equivalent to the original across entity set, fields, and graph edges.

## When the projection updates

The projection follows the DB **on its own**, with no manual command. ANY mutation
of an entity in one of the five projected kinds triggers it. That list is declared
once, in `state_serialize.ENTITY_DIRS`; both sides (export and import) derive from
it rather than keeping their own copy:

| Kind | What triggers it |
|---|---|
| `epics` | `epic add`, `epic done`, `epic delete` |
| `stories` | `story add`, `story done`, `story delete` |
| `tasks` | `task add/quick`, `update`, `start`, `log`, `plan`, `step`, `block`, `unblock`, `review`, `move`, `done`, `delete` |
| `decisions` | `decide` — every branch, including task-linked and brain-mirrored |
| `memory` | `memory add`, `dead-end`, `memory delete`, `memory link/unlink`, `memory archive` |

An entity that leaves the projection (deleted, or memory archived) **loses its
file**: the tree has to shrink as well as grow, or ghost files accumulate that
describe rows the DB no longer has.

Deliberately not triggering: `task claim` / `task unclaim`. `claimed_by` is not
among the columns `state_export.export_one` serializes, so they cannot change the
projection. That is the only exception, and it is checkable — the property below
would fail if it were wrong.

**How this is guaranteed.** Not by a list of call sites — that is exactly how the
first cut was built, and 18 of ~20 mutating methods skipped the export. The
guarantee is a property, checked by `tests/test_state_projection_tracks_db.py`:

> after any sequence of mutations, with no manual command in between, the files on
> disk equal `build_tree(db)` byte for byte

The property is indifferent to HOW the export happens, so a new mutator that
forgets to project fails the test, while a refactor that moves the export
elsewhere does not. Plus a coverage ratchet: the set of kinds the test exercises
is compared against `ENTITY_DIRS`, so a sixth kind cannot enter the registry
without extending the run.

**Cost.** The export re-renders the entity's whole document in order to compare it
with the file on disk. On the hottest mutator (`task log`) and the project's
longest journal — 21 entries, a 40 KB document — that is 26.6 ms against 5.3 ms
without the export. Measured, not estimated.

The whole mechanism sits behind `state.auto_export`; with the flag off nothing is
written and the tree only updates on an explicit `tausik state export`.

## Merging in git

- **Different entities** (A edited task X, B edited task Y) -> different files ->
  `git merge` merges cleanly.
- **Same entity** (both edited task X) -> a conflict in **one** file, resolved
  by hand. Localisation is the main win of "file per entity" over a binary DB,
  where the whole state would conflict.
- **The journal** of one task, appended on both branches -> git sees two groups
  of added lines; order is restored by sorting on `created_at` at the next
  import (append-only, so no semantic conflict).
- **Deleting an entity** = deleting the file. Import treats a missing file as
  "the entity is gone" ONLY on an explicit mirror-sync; ordinary incremental
  import does not delete (so `git checkout` of one branch does not erase tasks
  not yet merged from another). Deletion policy is refined in
  `state-git-import`.
- **Renaming a slug** = renaming the file (`git mv`). Since the slug is
  identity, a rename = new entity + delete old; links (`edges`, `story`,
  `defect_of`) are updated by export at the next write.

## Boundaries and errors (negative scenarios)

1. **Entity with no stable slug.** Before the `state-git-stable-ids` migration,
   decisions and part of memory have no slug. Exporting them **must be
   refused** with an explicit note that the migration is required first — not
   silently skipped, not given an ephemeral slug (which would drift across
   machines). Export depends on `state-git-stable-ids` by construction.
2. **Non-deterministic field.** Any set-valued field (tags, edges) without a
   sort rule yields a different file on different machines -> false conflicts.
   The normalisation rules above must remove non-determinism for EVERY such
   field; the round-trip gate catches any that are missed.
3. **Invalid frontmatter, hand-edited.** A file with broken YAML or a missing
   required field (`slug`) must be **rejected with an error naming the file and
   the problem** on import, not swallowed silently and not allowed to overwrite
   the DB with partial data. Silently swallowing broken state is exactly the
   class of silent error the project forbids.

## Dependencies

Implementation order is set by story `state-in-branch-mvp`. The load-bearing one
is `state-git-stable-ids`: without stable identity for decisions and memory,
export scenario (1) is impossible, and `memory_edges`/`decisions` on local
auto-increments would collide when two branches merge.
