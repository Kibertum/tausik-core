**English** | [Русский](../ru/hooks.md)

# Hooks (v1.3)

TAUSIK uses Claude Code hooks for automatic quality control. Hooks intercept agent actions **before** and **after** execution — they are gates, not instructions. **19 hooks** ship with v1.3.

## What Are Hooks

Hooks are scripts that run automatically with every agent action. They decide whether an action can be performed (PreToolUse), what to do afterward (PostToolUse), or what to record on session/agent boundaries (SessionStart, Stop, UserPromptSubmit). Shared helpers live in `scripts/hooks/_common.py`.

## PreToolUse — Gates That Run Before an Action

| Hook | When | What It Does |
|------|------|-------------|
| `task_gate.py` | Before Write/Edit | Blocks file changes if no active task (SENAR Rule 9.1) |
| `bash_firewall.py` | Before Bash | Blocks dangerous commands (rm -rf, DROP TABLE, force push, etc.) |
| `git_push_gate.py` | Before git push | Blocks direct push — use `/ship` or `/commit` |
| `memory_pretool_block.py` | Before Write to auto-memory | Blocks cross-project writes unless prompt contains `confirm: cross-project` |

## PostToolUse — Reactions After an Action

| Hook | When | What It Does |
|------|------|-------------|
| `auto_format.py` | After Write/Edit | Auto-formats with ruff/prettier/gofmt + logs "Modified: X" to task |
| `task_call_counter.py` | After any tool call | Increments per-task `call_actual` counter; warns at 1.5×budget |
| `activity_event.py` | After any tool call | Records activity timestamps for **gap-based active-time** session metric (SENAR Rule 9.2) |
| `memory_markers.py` | After Write/Edit | Detects memory marker patterns and routes to TAUSIK memory store |
| `memory_posttool_audit.py` | After Write to auto-memory | Audits cross-project leakage and warns |
| `brain_post_webfetch.py` | After WebFetch | Auto-caches result in shared brain `web_cache` for token reuse |
| `task_done_verify.py` | After `task_done` | Audits AC evidence via 5 rule-based checks (Ralph-mode-lite) |

## SessionStart / SessionEnd

| Hook | When | What It Does |
|------|------|-------------|
| `session_start.py` | On session start | Auto-injects status + Memory Block — no manual `/start` needed |
| `session_metrics.py` | On session end | Records session metrics (active vs wall, throughput) to DB |
| `session_cleanup_check.py` | On agent stop | Warns about open exploration / review tasks / session timeout |

## UserPromptSubmit / Stop

| Hook | When | What It Does |
|------|------|-------------|
| `user_prompt_submit.py` | On user prompt | Detects coding-intent (EN+RU) → nudges if no active task |
| `keyword_detector.py` | On agent stop | Catches "I'll implement"/"сейчас напишу" drift phrases → blocks stop |
| `brain_search_proactive.py` | Before WebSearch/WebFetch | Proactively queries shared brain for relevant decisions/patterns before web calls |

## Git pre-commit

| Hook | When | What It Does |
|------|------|-------------|
| `pre-commit` (shell) | Before `git commit` | Runs scoped quality gates; blocks commit on failure |

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
