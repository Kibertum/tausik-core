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

Use `tausik_task_show` with `slug={slug}` to load AC, plan steps, goal.

### 3. Verify Plan Completion

Check all plan steps are done. If not — warn which steps are incomplete. Ask: "Mark remaining steps done, or complete them first?"

### 4. Review Changes (full /review)

Run the full `/review` skill — NOT a lightweight check. Use the Agent tool to launch review in a subagent.

**Auto-escalate to deep mode** when the diff touches security-sensitive code (auth, payment, crypto, session handling, PII, secrets management) OR >5 files across multiple modules OR the task role is `security`/`architect`. In that case, append `deep` to the review scope so `/review` runs two sequential critic passes (see `harness/skills/review/SKILL.md` → "Adversarial Mode (built-in) → Deep mode").

**How to invoke:** Read `harness/skills/review/SKILL.md` yourself first, then pass the FULL contents as part of the Agent prompt (subagents cannot read files — they need instructions inline):

```
Agent(prompt: "[Paste full contents of review SKILL.md here]
Review scope: git diff (unstaged + staged changes) [append 'deep' if critical].
Task: {slug}, Goal: {goal}, AC: {AC}, Stack: {stack}.",
subagent_type: "general-purpose",
model: "sonnet")
```

> **Subagent model (phase=code-review):** review runs on **Sonnet 4.6** (`model="sonnet"`).
> Omitting `model=` is fine (inherits the session model) — a cost hint, not a requirement.
> Mapping: `docs/ru/research/model-routing-matrix.md`.

**If review verdict = FAIL (CRITICAL/HIGH issues):** Stop. Show issues. Do NOT proceed to commit. User must fix first.
**If review verdict = PASS or PASS WITH ISSUES (MEDIUM/LOW only):** Continue.

### 5. Run Tests (full /test)

Run the full `/test` skill — do NOT re-implement test logic here. Use the Agent tool to launch test in a subagent.

**How to invoke:** Read `harness/skills/test/SKILL.md` yourself first, then pass the FULL contents as part of the Agent prompt:

```
Agent(prompt: "[Paste full contents of test SKILL.md here]
Run tests for the current project. Stack: {stack}.",
subagent_type: "general-purpose",
model: "sonnet")
```

> **Subagent model (phase=code-review):** test/verification is a Sonnet-tier job
> (`model="sonnet"`). Omitting `model=` is fine — inherits the session model.

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

### 6. Verify Acceptance Criteria

Walk each AC from the task:
- State the criterion
- Verify it's met (check code, test output)
- Build evidence string

Log evidence: `tausik_task_log` with `slug={slug}`, `message="AC verified: 1. [criterion] ✓ [evidence] 2. [criterion] ✓ [evidence]"`

### 7. Commit (delegates to /commit)

Execute the `/commit` skill: read `harness/skills/commit/SKILL.md` and follow its full algorithm (stage → gates → message → confirm → commit → verify).

Reference task slug in the commit message body.

**If commit fails** (pre-commit hook, user declines): Stop. Do NOT close the task. Fix the issue and retry.

### 8. Close Task

**Only after successful commit AND step 5b verify green.**

**Preferred (v1.4+):** `tausik_task_done` — returns a structured JSON report with `stage` ("closed" | "blocked"), per-gate results, and a `blocking_failures` array the agent can iterate to fix issues without re-parsing prose. Use this whenever the project's MCP server exposes it.

```
tausik_task_done(
  slug={slug},
  ac_verified=True,
  relevant_files=[...]
)
```

**Fallback (legacy v1):** if the MCP server bundled with the project predates 1.3.7 and `tausik_task_done` is not in the tool list, fall back to `tausik_task_done` with the same arguments. v1 raises a single aggregated error string (1.4 fix, see CHANGELOG) — read it, fix, retry. Do **not** loop on failures silently.

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
