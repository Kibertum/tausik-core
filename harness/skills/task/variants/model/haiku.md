# /task — Haiku overlay

Work on tasks from project DB. **Never code without `task start` first.**

## $ARGUMENTS = slug

1. **Activate.** `tausik_task_start(slug)`. If QG-0 fails — set goal + AC via `tausik_task_update`, retry. No `--force`.
2. **Load.** `tausik_task_show(slug)` → goal, AC, plan steps, role, stack.
3. **Read role + stack.** `harness/roles/{role}.md` and `harness/stacks/{stack}.md`. Search memory: `tausik_memory_search`, `tausik_memory_list type=dead_end`.
4. **Brain primer.** If `tausik-brain` MCP available: `brain_search` with `category=patterns limit=3` and `category=gotchas limit=3`. Filter `brain.ignored:` ids. Skip silently if missing.
5. **Announce.** Role + title, goal, plan steps as checkboxes, AC numbered.
6. **Work plan steps in order.** After each step: `tausik_task_log(slug, "Step N done: ...")` then `tausik_task_step(slug, N)` (1-indexed).
7. **On failure.** `tausik_dead_end(approach, reason, task_slug=slug)`. Try alternative.
8. **All steps done.** Suggest: "Run `/ship` to review, test, and close." Do NOT call `/task done` directly.

## $ARGUMENTS = "done"

**Redirect to `/ship`.** Single closing path with full quality checks.

- If uncommitted changes (`git status --short`) → invoke `/ship`.
- If no changes:
  - `tausik_task_show(slug)` — verify plan complete
  - Walk AC, log evidence: `tausik_task_log(slug, "AC verified: 1. ✓ ... 2. ✓ ...")`
  - `tausik_verify(task_slug=slug)` — must pass before close
  - Close: `tausik_task_done(slug, ac_verified=true, relevant_files=[...])` (preferred) or `tausik_task_done` (legacy fallback)

## $ARGUMENTS = "list"

`tausik_task_list` → table with slug, title, status, complexity.

## $ARGUMENTS = "step N"

`tausik_task_step(slug, N)` (1-indexed). Log first.

## $ARGUMENTS = empty

`tausik_task_list(status="active")`. If one — show details with `task_show`. If none — suggest planning task.

## MCP tool reference

| Tool | Required | Optional |
|---|---|---|
| `tausik_task_start` | `slug` | — |
| `tausik_task_done` (preferred) | `slug` | `ac_verified`, `relevant_files`, `evidence`, `no_knowledge` |
| `tausik_task_done` (legacy) | `slug` | same args |
| `tausik_task_log` | `slug`, `message` | — |
| `tausik_task_step` | `slug`, `step_num` (1-based) | — |
| `tausik_task_show` | `slug` | — |
| `tausik_task_list` | — | `status`, `epic`, `story`, `stack`, `role`, `limit` |
| `tausik_task_update` | `slug` | `goal`, `acceptance_criteria`, `scope`, `complexity`, `stack`, `role`, `notes` |
| `tausik_dead_end` | `approach`, `reason` | `task_slug`, `tags` |
| `tausik_memory_search` | `query` | — |
| `tausik_memory_list` | — | `type`, `limit` |

## Rules

- QG-0: goal + AC required for `task start`. No shortcuts.
- QG-2: evidence + `ac_verified=true` required for close. No shortcuts.
- One active task at a time per agent. Second `task start` fails until first done/blocked.
- `task step` is **1-indexed**, must match plan step numbers.
- `task done` gated by plan steps — all must be marked done.
- Always `task log` before `task step` — log gives context, step marks completion.
- Document dead ends immediately via `tausik_dead_end` — don't repeat failed approaches.
- Auto-checkpoint reminder ~every 45 tool calls (SENAR Rule 9.3): "Consider `/checkpoint` to save context."
