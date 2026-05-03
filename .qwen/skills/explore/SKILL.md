---
name: explore
description: "SENAR exploration — time-bounded investigation before committing to a task. Use when user says 'explore', 'investigate', 'research', 'spike', or when facing an unfamiliar domain."
context: fork
effort: medium
---

# /explore — Time-Bounded Exploration (SENAR Section 5.1)

Investigation without full task formality.
**When to use:** Unfamiliar domain, multiple possible approaches, need to understand before planning.

**Key rule:** If exploration yields implementation work, a task SHALL be created before changes are committed.

## Argument Dispatch

### $ARGUMENTS = description of what to investigate

1. **Start exploration** via `tausik_explore_start` with `title="What we're investigating"` and `time_limit=30` (integer, minutes, default 30). Use shorter for simple questions, longer for complex domains.

2. **Announce:**
   - What we're investigating
   - Time limit
   - What we hope to learn

3. **Investigate:**
   - Read code, documentation, external resources
   - Try small experiments (do NOT write production code)
   - Document findings as you go in conversation

4. **Check time periodically** via `tausik_explore_current` MCP tool. If over time limit — wrap up immediately.

5. **End exploration with findings** via `tausik_explore_end` with `summary="What was discovered"` and optionally `create_task=true` to auto-create a task from findings.

6. **Document dead ends** via `tausik_dead_end` with `approach="What was tried"`, `reason="Why it failed"`. Check existing: `tausik_memory_list` with `type="dead_end"`.

7. **Suggest next:** "Findings recorded. Create a task with `/plan` or continue exploring."

### $ARGUMENTS = "end"

End current exploration via `tausik_explore_end` with `summary="Findings summary"`.

### $ARGUMENTS = "status" or empty

Check current exploration via `tausik_explore_current` (no params).

## Rules

- **Time-bounded.** Respect the time limit. When it's up, stop and summarize.
- **No production code.** Explorations are for learning, not implementing. Small experiments only.
- **If it yields work → create task.** Use `--create-task` or follow up with `/plan`.
- **Document everything.** Dead ends, findings, decisions — all captured.
- **Cheap to start, cheap to end.** Don't overthink the exploration scope.

## Gotchas

- **Only one active exploration** at a time. End the current one before starting another.
- **Explorations are not tasks** — no plan steps, no QG-0, no AC. Just investigate and report.
- **`--create-task` requires `--summary`** — you can't create a task without explaining what you found.
