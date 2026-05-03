# /plan — Haiku overlay

Plan a task. Follow steps in order. No improvisation.

## Steps

1. **Interview.** If request is vague, invoke `/interview` skill (max 3 questions). Skip if `--skip-interview` or detailed spec given. Save spec via `tausik_task_log` after task created.

2. **Score complexity.** Count signals (domains, files, risk):
   - 1-2 → simple (1 task)
   - 3-5 → medium (2-3 tasks)
   - 6+ → complex (decompose)

3. **Check knowledge.** Run:
   - `tausik_memory_search` — patterns
   - `tausik_memory_list type=dead_end` — past failures
   - `brain_search category=patterns limit=3` and `category=gotchas limit=3` (skip if brain MCP missing). Filter ids matching `brain.ignored:` conventions.

4. **Detect stack.** From package.json / requirements.txt / go.mod. Default role = `developer`.

5. **Create task.** MCP-first:
   - Auto-slug: `tausik_task_quick(title=..., goal=..., role="developer", stack=...)`
   - Explicit: `tausik_task_add(slug=..., title=..., goal=..., role=..., stack=..., complexity=...)`

6. **Set call budget.** `tausik_task_update(slug=..., call_budget=N)`. Tiers:
   - trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400

7. **Set acceptance criteria (MANDATORY — QG-0 blocks without it).**
   `tausik_task_update(slug=..., acceptance_criteria="1. ... 2. ... 3. ...")`
   Each criterion testable. Include at least one negative scenario. No vague text.

8. **Set plan steps.** `tausik_task_plan(slug=..., steps=[...])`

9. **Present.** Show: slug, title, complexity, role, goal, plan steps, AC. Suggest: "Run `/task {slug}` to start."

## Tier reference

`call_budget` value sets `tier` automatically:

| Tier | Budget | Example |
|---|---|---|
| trivial | ≤10 | one-line config tweak |
| light | ≤25 | migration + helpers + tests |
| moderate | ≤60 | hook + service + tests |
| substantial | ≤150 | CLI + service + MCP + mirror |
| deep | ≤400 | full vertical feature |

Skipping budget is allowed but flag it — calibration breaks without `call_budget`/`call_actual`.

## CLI fallback (if MCP unavailable)

```
.tausik/tausik task quick "Title" --role developer --stack python --goal "..."
.tausik/tausik task add "Title" --slug my-task --complexity medium --role developer --stack python --goal "..."
.tausik/tausik task update <slug> --acceptance-criteria "1. ... 2. ..."
.tausik/tausik task plan <slug> "Step 1" "Step 2"
```

## Rules

- Slug: `^[a-z0-9][a-z0-9-]*$`, max 64 chars.
- Roles: free-text (any string).
- Epic/story: optional. For grouped work: `epic add` then `story add` first.
- Defect: add `--defect-of <parent-slug>`.
- Without goal + AC, `task start` will fail QG-0 (no bypass).
- Unfamiliar domain → suggest `.tausik/tausik explore start "..."` before planning.
