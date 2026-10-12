---
name: ship
description: "Ship — review + test + gates + commit in one shot."
context: fork
effort: slow
---

# /ship — Ship It (Solo Workflow)

Review + test + gates + AC verify + task done + commit — all in one.
## When to Use

- User says "ship it", "done", "wrap up", "готово", "отправляй"
- Work is complete and user wants to close everything cleanly

## Algorithm

### 1. Find Active Task

Use `tausik_task_list` MCP tool with `status=active`.

If no active task — check git status for uncommitted changes and offer just commit.

### 2. Get Task Context

Use `tausik_task_show` with `slug={slug}, mode="package"` to load AC, plan
steps, goal, and `required.review_route`. The route is produced by the
canonical dispatcher; do not infer depth from stack, role, file names, or skill
prose.

### 3. Verify Plan Completion

Check that the implementation steps are done. Persist each completed step with
`tausik_task_step(message=...)`. Exactly one final verification/closure step may
remain pending for the compound close in step 8; any other incomplete work stops
the ship workflow.

### 4. Execute `required.review_route`

Follow the route verbatim. Keep deterministic gates in every lane.

> **Subagent route (phase=code-review):** use the exact reviewer depth, context,
> model-family separation, and invocation count returned by `required.review_route`.
> Use Terra on Codex for the focused balanced reviewer; the equivalent Claude
> Agent call declares `model: "sonnet"`.

- **L1**: run every selected profile checklist and the deterministic gates.
  Launch zero reviewer subagents. Record L1 with zero invocations.
- **L2**: launch exactly one focused reviewer in a fresh context. It checks the
  residual gaps, AC wiring, changed behavior, and selected profile checklists.
  Record L2 with `reviewer_context=fresh`.
- **L3**: launch exactly one external reviewer on a different model family via
  `tausik-external-reviewer`. Separate context on the author's model is still
  L2. If a different model is unavailable, stop; never downgrade.
- **L3-deep**: launch the multi-agent `/review` flow only when the dispatcher
  returns `deep=true`. That occurs only for an explicit deep audit or a
  configured extreme hard floor.

For every lane, persist the actual depth, author/reviewer models, selected
profiles, route reasons, hard floor, reviewer invocation count, and available
task usage through `tausik review record`. HIGH or CRITICAL findings stop
shipping. After a substantive repair, re-run deterministic verification and
re-review the repaired files before recording a passing run.

Do not treat lint or schema validation as evidence of behavior, idempotence,
rollback, or postconditions. Only capabilities in the signed receipt count.

### 5. Run Tests (full /test)

Run the full `/test` skill — do NOT re-implement test logic here. Use the Agent tool to launch test in a subagent.

**How to invoke:** Read `harness/skills/test/SKILL.md` yourself first, then pass the FULL contents as part of the Agent prompt:

```
Agent(prompt: "[Paste full contents of test SKILL.md here]
Run tests for the current project. Stack: {stack}.",
subagent_type: "general-purpose",
model: "sonnet")
```

> **Subagent route (phase=verification):** use the same balanced family tier as
> review. A failed verification escalates the diagnostic worker one tier; the
> coordinator still runs the final verify and closes the task.

**If tests fail:** Stop. Show failures. Do NOT proceed. User must fix first.
**If tests pass:** Continue.

### 5b. Run `tausik verify` (Verify-First Contract, v1.4)

Heavy gates (pytest, tsc, cargo, phpstan, etc.) no longer fire automatically inside `task_done`. Trigger them explicitly via `tausik_verify` MCP tool (or `.tausik/tausik verify --task {slug}` as fallback). The result is cached for 10 minutes — `task_done` will look it up and close instantly.

**How to invoke:**

```
tausik_verify(task_slug={slug})
```

**Possible outcomes:**

- `passed=True, status="hit"` — cached green, no work re-done. Continue to step 6.
- `passed=True, status="miss"` — fresh run completed and cached. Continue to step 6.
- `passed=True, status="bypass"` — security-sensitive files; cache is intentionally refused, fresh run done. Continue to step 6.
- `passed=False` — at least one verify gate failed. Stop. Show output, fix, retry.

**Opt-out (CI/inline):** if the project sets `{"task_done": {"auto_verify": true}}` in `.tausik/config.json`, you can skip step 5b — `task_done` will run the verify gates inline. This is rare; prefer the explicit verify call so the user sees timings and can interrupt.

If the final plan step is the verification/closure step, defer this verify until
after the required commit and run it through the step 8 compound close
(`verify=true`). Do not run both paths. A red compound verification returns its
diagnostic and leaves the task open.

### 6. Verify Acceptance Criteria

Reload the task in package mode before evaluating AC. A measured-high closure
may raise an earlier L1/L2 route to L3. If the route increased, execute and
record the stronger review before continuing.

Walk each AC from the task:
- State the criterion
- Verify it's met (check code, test output)
- Build evidence string

Build the evidence string for the close call. If using the separate verify path,
it may also be logged now. If using compound close, supply it as `evidence` so
the existing close operation records it once.

### 7. Commit (delegates to /commit)

Execute the `/commit` skill: read `harness/skills/commit/SKILL.md` and follow its full algorithm (stage → gates → message → confirm → commit → verify).

Reference task slug in the commit message body.

**If commit fails** (pre-commit hook, user declines): Stop. Do NOT close the task. Fix the issue and retry.

### 8. Close Task

**Only after successful commit and either a green step 5b verify or the compound verification below.**

**Preferred (v1.4+):** `tausik_task_done` — returns a structured JSON report with `stage` ("closed" | "blocked"), per-gate results, and a `blocking_failures` array the agent can iterate to fix issues without re-parsing prose. Use this whenever the project's MCP server exposes it.

```
tausik_task_done(
  slug={slug},
  ac_verified=True,
  relevant_files=[...]
)
```

**Fallback (legacy v1):** if the MCP server bundled with the project predates 1.3.7 and `tausik_task_done` is not in the tool list, fall back to `tausik_task_done` with the same arguments. v1 raises a single aggregated error string (1.4 fix, see CHANGELOG) — read it, fix, retry. Do **not** loop on failures silently.

When one final verification/closure step remains, fold the deterministic
transitions into that same call:

```
tausik_task_done(
  slug={slug},
  compound='{"message":"Final verification complete","step":N,"verify":true}',
  ac_verified=True,
  evidence={ac_evidence},
  relevant_files=[...]
)
```

The service executes `task_log`, `task_step`, verification, and `task_done` in
that order. Earlier successful transitions remain durable if a later stage
refuses. Supply either `verify=true` in `compound` or `verify_handle`, never both.

Verify-First Contract: both v1 and v2 look up the cached green from step 5b. If you skipped step 5b on a project with verify-trigger gates, `task_done` will refuse to close — go back, run `tausik_verify`, then retry.

### 9. Update Documentation (auto)

After commit, check if structural changes were made (new files, renamed modules, changed APIs):
- Run `git diff --name-only HEAD~1` to see changed files
- If files in `scripts/`, `harness/`, `bootstrap/`, or core modules changed — suggest updating `references/` documentation
- Update only files in `references/` that are directly affected (e.g., `architecture.md`, `project-cli.md`)
- Do NOT touch `CLAUDE.md`, `QWEN.md`, or `.cursorrules` — those are managed by bootstrap
- If no structural changes — skip silently

### 10. Push (optional)

After commit + task close, ask the user: **"Push to remote? (y/n)"**

If confirmed, follow the push procedure from `/commit` skill (step 8).

### 11. Summary

Show:
- Task completed: slug + title
- Gate results: pass/warn
- Commit hash
- Push status (pushed to origin/branch or skipped)
- Suggest: "Next task? Use `/task list` to pick one, or `/end` to wrap up the session."

## Edge Cases

- **AC verification fails**: Stop, report which AC failed, suggest what to fix
- **No tests exist**: Warn but don't block (suggest writing tests)
- **Multiple active tasks**: Compare `git diff --name-only` against each task's `scope` field (from `tausik_task_show`). If no scope set, ask the user which task to ship
- **Nothing to commit**: Skip commit step, just close task
- **Push gate blocks**: Run `tausik push-ok && git push` — `push-ok` writes a single-use 60s ticket bound to HEAD SHA; this skill is authorized to do so only after user confirmation

## Gotchas

- **Do not ship without user confirmation for push.** The "Push to remote?" prompt is non-negotiable; CI auto-push is a separate story.
- **Gate failures stop the ship early.** If ruff/pytest fails, do NOT force-commit — fix the root cause first.
- **AC evidence format matters.** QG-2 parses notes for "✓" and test counts; commits without evidence in task_log will be blocked by the task_done gate.
- **Multiple active tasks create scope ambiguity.** If the diff spans two tasks' scope, ask the user which task this ship belongs to — do not guess.
- **Don't amend the ship commit after push.** Pushing then amending forces the user to force-push; create a follow-up commit instead.
