# /ship — Sonnet overlay

Review + test + gates + AC verify + task done + commit — all in one (solo workflow).

## When to Use

- User says "ship it", "done", "wrap up", "готово", "отправляй"
- Work is complete and user wants to close everything cleanly

## Algorithm

### 1. Find Active Task

`tausik_task_list(status="active")`. If none — check `git status`, offer plain commit.

### 2. Get Task Context

`tausik_task_show(slug)` → AC, plan steps, goal.

### 3. Verify Plan Completion

All plan steps done? If not — warn which are incomplete. Ask: "Mark remaining done, or complete first?"

### 4. Review Changes (full /review)

Run full `/review` in a subagent — NOT a lightweight check.

**Auto-escalate to deep mode** when diff touches security-sensitive code (auth, payment, crypto, session, PII, secrets) OR >5 files across modules OR role is `security`/`architect`. Append `deep` to review scope.

**Invoke:** Read `harness/skills/review/SKILL.md`, pass FULL contents inline to the Agent (subagents can't read files):

```
Agent(prompt: "[Paste full review SKILL.md]
Review scope: git diff (unstaged + staged) [append 'deep' if critical].
Task: {slug}, Goal: {goal}, AC: {AC}, Stack: {stack}.",
subagent_type: "general-purpose")
```

- **FAIL (CRITICAL/HIGH):** Stop. Show issues. Do NOT commit. User fixes first.
- **PASS / PASS WITH ISSUES (MEDIUM/LOW):** Continue.

### 5. Run Tests (full /test)

Run full `/test` in subagent. Read `harness/skills/test/SKILL.md`, paste FULL contents into Agent prompt with `Stack: {stack}`.

- Tests fail → Stop. Fix first.
- Pass → Continue.

### 5b. Run `tausik verify` (Verify-First Contract, v1.4)

Heavy gates (pytest, tsc, cargo, phpstan) no longer fire automatically inside `task_done`. Trigger explicitly:

```
tausik_verify(task_slug={slug})
```

Outcomes:
- `passed=True, status="hit"` — cached green, no re-run. Continue.
- `passed=True, status="miss"` — fresh run completed and cached. Continue.
- `passed=True, status="bypass"` — security-sensitive files; cache refused, fresh run done. Continue.
- `passed=False` — verify gate failed. Stop. Show output, fix, retry.

**Opt-out:** if `.tausik/config.json` has `{"task_done": {"auto_verify": true}}`, you may skip — `task_done` runs verify inline. Rare; prefer explicit verify so user sees timings.

### 6. Verify Acceptance Criteria

Walk each AC: state criterion, verify met (code/test output), build evidence string.

Log: `tausik_task_log(slug, "AC verified: 1. [criterion] ✓ [evidence] 2. [criterion] ✓ [evidence]")`.

### 7. Commit (delegates to /commit)

Execute `/commit` skill: read `harness/skills/commit/SKILL.md`, follow full algorithm (stage → gates → message → confirm → commit → verify). Reference task slug in body.

Commit fails (pre-commit hook, user declines) → Stop. Do NOT close task.

### 8. Close Task

**Only after successful commit AND step 5b green.**

**Preferred (v1.4+):** `tausik_task_done` returns structured JSON with `stage` ("closed" | "blocked"), per-gate results, `blocking_failures` array.

```
tausik_task_done(slug, ac_verified=True, relevant_files=[...])
```

**Fallback (legacy v1):** if `tausik_task_done` not in tool list, use `tausik_task_done` with same args. v1 raises aggregated error string — read, fix, retry. Do NOT loop on failures silently.

Verify-First: both v1 and v2 look up step 5b cache. Skipping 5b on verify-trigger projects → `task_done` refuses. Run verify, retry.

### 9. Update Documentation (auto)

After commit, `git diff --name-only HEAD~1`. Structural changes in `scripts/`, `harness/`, `bootstrap/`, core → suggest updating `references/` (only directly affected files like `architecture.md`, `project-cli.md`). Skip `CLAUDE.md`, `QWEN.md`, `.cursorrules` (managed by bootstrap). No structural changes → skip silently.

### 10. Push (optional)

Ask: **"Push to remote? (y/n)"**. If yes, follow push procedure from `/commit` step 8.

### 11. Summary

Show: slug + title, gate results (pass/warn), commit hash, push status. Suggest `/task list` or `/end`.

## Edge Cases

- **AC fail:** Stop, report which AC failed, suggest fix.
- **No tests:** Warn, don't block.
- **Multiple active tasks:** Compare `git diff --name-only` to each task's `scope` (from `tausik_task_show`). No scope → ask user.
- **Nothing to commit:** Skip commit, just close.
- **Push gate blocks:** Run `tausik push-ok && git push` — `push-ok` writes a single-use 60s ticket bound to HEAD SHA; this skill is authorized to do so after confirmation.

## Gotchas

- **No push without user confirmation.** Non-negotiable.
- **Gate failures stop ship.** Fix root cause, never force-commit.
- **AC evidence format matters.** QG-2 parses for "✓" and test counts; commits without evidence in `task_log` blocked by `task_done` gate.
- **Multiple active tasks → scope ambiguity.** Diff spans two tasks → ask user, don't guess.
- **Don't amend after push.** Forces user to force-push; create follow-up commit.
