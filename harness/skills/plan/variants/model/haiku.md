# /plan — Haiku overlay

Plan a task. Follow steps in order. No improvisation.

## Steps

1. **Interview.** If request is vague, invoke `/interview` skill (max 3 questions). Skip if `--skip-interview` or detailed spec given. Fold the spec into `tausik_task_add` `rationale` — never journal the new slug before `task start`.

2. **Score complexity.** Count signals (domains, files, risk):
   - 1-2 → simple (1 task)
   - 3-5 → medium (2-3 tasks)
   - 6+ → complex (decompose)

3. **Check knowledge.** Run:
   - `tausik_memory_search` — patterns
   - `tausik_memory_list type=dead_end` — past failures

4. **Detect stack.** From package.json / requirements.txt / go.mod. Default role = `developer`.

5. **Create the complete task atomically.** Call `tausik_task_add` once with
   `slug`, `title`, `goal`, `acceptance_criteria`, `scope`, `scope_paths`,
   `rollback_plan`, `call_budget`, `plan_steps`, `rationale`, and optional
   `depends_on`. Create graphs in topological order.

6. **Set call budget in that task-add call.** Tiers:
   - trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400

7. **Set acceptance criteria in that task-add call (MANDATORY — QG-0 blocks without it).**
   Each criterion testable. Include at least one negative scenario. No vague text.

8. **Set `plan_steps` in that task-add call.**

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
.tausik/tausik task add "Title" --slug my-task --complexity medium --role developer --stack python --goal "..." --acceptance-criteria "AC-1 succeeds. Negative: invalid input fails." --call-budget 25 --step "Step 1" --step "Step 2"
```

## Rules

- Slug: `^[a-z0-9][a-z0-9-]*$`, max 64 chars.
- Roles: free-text (any string).
- Epic/story: optional. For grouped work: `epic add` then `story add` first.
- Defect: add `--defect-of <parent-slug>`.
- Without goal + AC, `task start` will fail QG-0 (no bypass).
- Unfamiliar domain → suggest `.tausik/tausik explore start "..."` before planning.
- Never work around `TASK_BINDING_MISMATCH`; use the atomic task-add fields.
