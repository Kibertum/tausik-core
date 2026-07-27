**English** | [Русский](/ru/docs/hooks)

# Hooks

TAUSIK uses Claude Code hooks for automatic quality control. Hooks intercept agent actions **before** and **after** execution — they are gates, not instructions. **22 Python hooks + 1 shell `pre-commit`** ship with TAUSIK — 23 gates in total (v1.4 introduced `secret_scan.py`, `posttool_usage.py`, `tool_output_truncation_nudge.py`, and `task_cost_budget_check.py`; 1.8 added `scope_write_gate.py` and `bash_write_gate.py`).

## What Are Hooks

Hooks are scripts that run automatically with every agent action. They decide whether an action can be performed (PreToolUse), what to do afterward (PostToolUse), or what to record on session/agent boundaries (SessionStart, Stop, UserPromptSubmit). Shared helpers live in `scripts/hooks/_common.py` (not a hook itself); the regex set in `scripts/hooks/memory_markers.py` is a library imported by `memory_posttool_audit.py` and the brain-scrubbing pipeline.

## PreToolUse — Gates That Run Before an Action

| Hook | When | What It Does |
|------|------|-------------|
| `task_gate.py` | Before Write/Edit | Blocks file changes if no active task (SENAR Rule 9.1) |
| `scope_write_gate.py` | Before Write/Edit/MultiEdit/NotebookEdit | Scope ACL (SENAR Rule 2, Walko pattern): blocks a write outside the union of the active tasks' declared `scope_paths`. This is the verdict source `bash_write_gate` reuses for shell writes. Conservative adoption: any active task without `scope_paths` → allow (legacy, undeclared = unrestricted); target outside the project root → allow; pre-v30 DB or any DB error → fail-open unless `TAUSIK_HOOK_FAIL_SECURE=1`. |
| `memory_pretool_block.py` | Before Write/Edit/MultiEdit **and Bash/PowerShell** | Layer 2 of memory-route enforcement: blocks a write into any foreign memory sink from `scripts/memory_sinks.py` (`~/.claude/**/memory/`, `.cursor/rules/`, `.github/copilot-instructions.md`, `.aider*`, …) and redirects to `memory add`. The shell tools are on the matcher because a heredoc — or a `Set-Content` — writes what the Write path refuses. Bypass: `confirm: cross-project` in the prompt, or `gates.memory_route.allow` in config. |
| `secret_scan.py` (v1.4) | Before Write/Edit/MultiEdit | Scans `tool_input` for likely secrets (AWS/GitHub/Slack/Stripe/OpenAI/Anthropic tokens, JWT, private-key blocks, generic `password`/`api_key` literals). Warns by default; set `TAUSIK_SECRET_SCAN_STRICT=1` to block. (SENAR Rule 10.12). **Covers neither shell channel** — not Bash, not PowerShell; see the channel-coverage matrix in [`enforcement-coverage.md`](enforcement-coverage.md). |
| `bash_firewall.py` | Before Bash **and PowerShell** | Blocks dangerous commands (`rm -rf /`, `Remove-Item -Recurse C:\`, DROP TABLE, `Format-Volume`, force push, etc.). The dialect is chosen by `tool_name`: the POSIX lexer cannot read PowerShell, where `\` is an ordinary path character rather than an escape. |
| `bash_write_gate.py` | Before Bash **and PowerShell** | Applies the same QG-0 (Rule 1) and scope-ACL (Rule 2) verdict to a shell write that the Write tool gets — by importing `scope_write_gate`'s decisions, not copying them. Parses redirections, `tee`/`dd`/`sed -i`/`cp`/`mv`, and `Set-Content`/`Add-Content`/`Out-File`/`New-Item`/`Tee-Object`. |
| `brain_search_proactive.py` | Before WebSearch/WebFetch | Proactively queries shared brain for relevant decisions/patterns before web calls |
| `git_push_gate.py` | Before Bash **and PowerShell** | Blocks unless `.tausik/.push_ticket.json` is fresh, single-use, and bound to HEAD SHA. `/ship` and `/commit` run `tausik push-ok && git push` after your "y" — `push-ok` writes the 60-second ticket; the hook consumes it on the next push. The narrowing `if` clause is gone: it was a second copy of a decision the hook makes itself, and it named only one shell. |

## PostToolUse — Reactions After an Action

| Hook | When | What It Does |
|------|------|-------------|
| `auto_format.py` | After Write/Edit | Auto-formats with ruff/prettier/gofmt + logs "Modified: X" to task |
| `memory_posttool_audit.py` | After Write/Edit/MultiEdit to auto-memory | Audits cross-project leakage (uses `memory_markers.py` regex library) and warns |
| `task_done_verify.py` | After `mcp__tausik-project__tausik_task_done` | Audits AC evidence via 5 rule-based checks (Ralph-mode-lite). |
| `brain_post_webfetch.py` | After WebFetch | Auto-caches result in shared brain `web_cache` for token reuse |
| `task_call_counter.py` | After any tool call | Increments per-task `call_actual` counter; warns at 1.5×budget |
| `posttool_usage.py` (v1.4) | After any tool call | Records token-usage events to `usage_events` for per-task cost rollup |
| `activity_event.py` | After any tool call | Records activity timestamps for **gap-based active-time** session metric (SENAR Rule 9.2) |
| `tool_output_truncation_nudge.py` (v1.4) | After Read/Grep/Bash/Glob | Coaches the agent to narrow scope when tool output exceeds the configured line threshold (warn-only) |
| `task_cost_budget_check.py` (v1.4) | After any tool call | Compares the active task's `cost_actual` / `tokens_actual` against budget; emits WARN at 1.5× and BLOCKER at 2× (throttled) |

## SessionStart

| Hook | When | What It Does |
|------|------|-------------|
| `session_start.py` | On session start | Auto-injects status + Memory Block + rebuilds skill profiles — no manual `/start` needed |

## UserPromptSubmit

| Hook | When | What It Does |
|------|------|-------------|
| `user_prompt_submit.py` | On user prompt | Detects coding-intent (EN+RU) → nudges if no active task; detects code-discovery intent ("where is X") → nudges toward `search_code`. Ignores slash-command bodies and hook-generated text |

## Stop

| Hook | When | What It Does |
|------|------|-------------|
| `keyword_detector.py` | On agent stop | Catches "I'll implement"/"сейчас напишу" drift phrases → blocks stop |
| `session_cleanup_check.py` | On agent stop | Warns about open exploration / review tasks / session timeout |

## SessionEnd

| Hook | When | What It Does |
|------|------|-------------|
| `session_metrics.py` | On session end | Records session metrics (active vs wall, throughput) to DB |

## Git pre-commit

| Hook | When | What It Does |
|------|------|-------------|
| `pre-commit` (shell) | Before `git commit` | Runs `python -m mypy` against `scripts/` (uses `pyproject.toml` config). On exit ≠ 0 — **blocks the commit**. Optionally runs an incremental `codebase-rag` reindex (warn-only, capped at 5s); never blocks the commit because of RAG. |

This is **not** "scoped quality gates" — those run via `tausik verify` (heavy stack: pytest/tsc/cargo/phpstan/…) and are decoupled from `git commit` since the v1.4 Verify-First Contract.

### Install (one-time)

```bash
# Option A: copy the file
cp scripts/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Option B (recommended): point git at the in-repo hooks dir so updates are picked up automatically
git config core.hooksPath scripts/hooks
```

> **Windows caveat.** `pre-commit` is a Bash script with `timeout(1)` and POSIX `[ -f … ]`. Plain `cmd.exe` will fail to execute it. Use Git Bash, WSL, or a terminal that ships Bash + `timeout` on `PATH`. If your team runs Windows-only, replace the script with a `pre-commit.cmd` wrapper that calls `python -m mypy` directly and accepts the same exit contract.

### Disable / bypass

- One-off: `git commit --no-verify` (skips `core.hooksPath` entirely).
- Temporarily: `git config --unset core.hooksPath`.
- For CI without mypy: keep `core.hooksPath` unset on CI runners; the heavy verification runs via `tausik verify` regardless.

## How It Works

```
You: "add a button to the homepage"

Agent wants to edit index.html
  → task_gate.py checks: is there an active task? No → BLOCKED
  → Agent creates a task via /plan, starts
  → task_gate.py checks again: task exists → ALLOWED

Agent edits index.html
  → auto_format.py: formats with prettier
  → auto_format.py: logs "Modified: index.html" to the task
  → task_call_counter.py: bumps call_actual; warns at 1.5×budget
  → activity_event.py: stamps activity timestamp (active-time)

Agent: tausik task done my-button --ac-verified
  → task_done_verify.py: 5-check AC audit
```

## Exit Codes

| Code | Meaning | Behavior |
|------|---------|----------|
| 0 | Success | Action allowed |
| 1 | Warning | Action allowed; warning logged |
| 2 | Block | Action **cancelled**; agent receives the reason |

## What `bash_firewall` Blocks

- `rm -rf /` and `rm -rf .` — filesystem deletion
- `DROP TABLE`, `DROP DATABASE`, `TRUNCATE TABLE` — data deletion
- `git reset --hard` — loss of local changes
- `git push --force` — overwriting remote history
- `git clean -fd` — deleting untracked files
- `dd if=/dev/zero`, `mkfs.` — disk formatting
- Fork bombs

## Disabling Hooks

For testing or debugging: set `TAUSIK_SKIP_HOOKS=1`.

In `.claude/settings.json` hooks are generated automatically during bootstrap. To disable a specific hook, remove it from the `hooks` section. To re-generate the file, run `python .tausik-lib/bootstrap/bootstrap.py --refresh`.

## What's Next

- **[Workflow](workflow.md)** — how hooks fit the work cycle
- **[Session Active Time](session-active-time.md)** — what `activity_event.py` powers
- **[CLI Commands](cli.md)** — managing tasks from the terminal
