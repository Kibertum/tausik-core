---
name: ship
description: "Wrap up current work: review + test + gates + commit in one operation. Use when user says 'ship', 'ship it', 'wrap up', 'done', 'finish', 'готово', 'отправляй', 'заверши', 'закрывай'."
context: fork
effort: slow
---

# /ship — Ship It (Solo Workflow)

Review + test + gates + AC verify + task done + commit — all in one. Always respond in the user's language.

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

**How to invoke:** Read `agents/skills/review/SKILL.md` yourself first, then pass the FULL contents as part of the Agent prompt (subagents cannot read files — they need instructions inline):

```
Agent(prompt: "[Paste full contents of review SKILL.md here]
Review scope: git diff (unstaged + staged changes).
Task: {slug}, Goal: {goal}, AC: {AC}, Stack: {stack}.",
subagent_type: "general-purpose")
```

**If review verdict = FAIL (CRITICAL/HIGH issues):** Stop. Show issues. Do NOT proceed to commit. User must fix first.
**If review verdict = PASS or PASS WITH ISSUES (MEDIUM/LOW only):** Continue.

### 5. Run Tests (full /test)

Run the full `/test` skill — do NOT re-implement test logic here. Use the Agent tool to launch test in a subagent.

**How to invoke:** Read `agents/skills/test/SKILL.md` yourself first, then pass the FULL contents as part of the Agent prompt:

```
Agent(prompt: "[Paste full contents of test SKILL.md here]
Run tests for the current project. Stack: {stack}.",
subagent_type: "general-purpose")
```

Quality gates run automatically on `tausik_task_done` in step 7.

**If tests fail:** Stop. Show failures. Do NOT proceed. User must fix first.
**If tests pass:** Continue.

### 6. Verify Acceptance Criteria

Walk each AC from the task:
- State the criterion
- Verify it's met (check code, test output)
- Build evidence string

Log evidence: `tausik_task_log` with `slug={slug}`, `message="AC verified: 1. [criterion] ✓ [evidence] 2. [criterion] ✓ [evidence]"`

### 7. Commit (delegates to /commit)

Execute the `/commit` skill: read `agents/skills/commit/SKILL.md` and follow its full algorithm (stage → gates → message → confirm → commit → verify).

Reference task slug in the commit message body.

**If commit fails** (pre-commit hook, user declines): Stop. Do NOT close the task. Fix the issue and retry.

### 8. Close Task

**Only after successful commit.** Use `tausik_task_done` with `slug={slug}`, `ac_verified=true`, `relevant_files=[...]` (files from the commit).

### 9. Push (optional)

After commit + task close, ask the user: **"Push to remote? (y/n)"**

If confirmed, follow the push procedure from `/commit` skill (step 8).

### 10. Summary

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
- **Push gate blocks**: Use `TAUSIK_ALLOW_PUSH=1` env — this skill is authorized to push after user confirmation
