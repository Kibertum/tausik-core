# /ship — Haiku overlay

Review + test + verify + commit + close — one operation.

## Steps

1. **Find active task.** `tausik_task_list(status="active")`. If none → check `git status`, offer plain commit.

2. **Load context.** `tausik_task_show(slug)` → AC, plan steps, goal.

3. **Verify plan complete.** All steps done? If not — warn, ask user to mark or finish first.

4. **Run `/review` in subagent.** Read `harness/skills/review/SKILL.md`, paste full contents into Agent prompt with task slug, goal, AC, stack.
   - **Auto-escalate to deep mode** if diff touches auth/payment/crypto/session/PII/secrets, OR >5 files multi-module, OR role is `security`/`architect`. Append `deep` to scope.
   - Verdict FAIL (CRITICAL/HIGH) → STOP. Show issues. Do NOT commit.
   - Verdict PASS or PASS WITH ISSUES → continue.

5. **Run `/test` in subagent.** Read `harness/skills/test/SKILL.md`, paste full contents into Agent prompt. Stack = task stack.
   - Tests fail → STOP. Fix first.
   - Pass → continue.

6. **Run verify (Verify-First, v1.4).** `tausik_verify(task_slug=slug)`.
   - `passed=False` → STOP, fix, retry.
   - `passed=True` (hit/miss/bypass) → continue.
   - Skip only if config has `task_done.auto_verify=true`.

7. **Verify AC.** Walk each criterion, build evidence. Log: `tausik_task_log(slug, "AC verified: 1. [crit] ✓ [evidence] 2. ...")`.

8. **Commit via `/commit` skill.** Read `harness/skills/commit/SKILL.md`, follow its full algorithm. Reference task slug in body. Commit fails → STOP, do NOT close task.

9. **Close task.** Only after successful commit + step 6 green.
   - Preferred: `tausik_task_done(slug, ac_verified=true, relevant_files=[...])`
   - Legacy fallback: `tausik_task_done` with same args.
   - If you skipped step 6 on verify-trigger gates, close refuses — go run verify first.

10. **Update docs (auto).** `git diff --name-only HEAD~1`. Structural changes in `scripts/`, `harness/`, `bootstrap/`, core → suggest updating `references/`. Skip `CLAUDE.md`, `QWEN.md`, `.cursorrules`. No structural changes → skip silently.

11. **Push (optional).** Ask: "Push to remote? (y/n)". If yes — follow `/commit` step 8: `tausik push-ok && git push` (single-use 60s ticket).

12. **Summary.** Slug + title, gate results, commit hash, push status. Suggest `/task list` or `/end`.

## Edge Cases

- **AC verification fails** → stop, report which AC failed, suggest fix.
- **No tests exist** → warn but don't block (suggest writing tests).
- **Multiple active tasks** → compare `git diff --name-only` against each task's `scope` from `tausik_task_show`. No scope set → ask user which task to ship.
- **Nothing to commit** → skip commit step, just close task.
- **Push gate blocks** → run `tausik push-ok && git push`. `push-ok` writes single-use 60s ticket; skill authorized after user confirmation.

## Rules

- **Do not push without user confirmation.** The "Push to remote?" prompt is non-negotiable; CI auto-push is a separate story.
- **Gate failures stop ship early.** If ruff/pytest fails, do NOT force-commit — fix root cause first.
- **AC evidence format matters.** QG-2 parses notes for "✓" and test counts; commits without evidence in `task_log` are blocked by `task_done` gate.
- **Multiple active tasks → scope ambiguity.** If diff spans two tasks' scope, ask user which task this ship belongs to — don't guess.
- **Don't amend the ship commit after push.** Pushing then amending forces user to force-push; create follow-up commit instead.
