**English** | [Русский](../ru/hooks.md)

# Hooks

TAUSIK uses Claude Code hooks for automatic quality control.
Hooks intercept agent actions **before** and **after** execution — they are gates,
not instructions.

## What Are Hooks

Hooks are scripts that run automatically with every agent action.
They decide whether an action can be performed (PreToolUse) or what to do afterward (PostToolUse).

| Hook | When | What It Does |
|------|------|-------------|
| `task_gate.py` | Before Write/Edit | Blocks file changes if there is no active task |
| `bash_firewall.py` | Before Bash | Blocks dangerous commands (rm -rf, DROP TABLE, etc.) |
| `git_push_gate.py` | Before git push | Blocks direct push — use /ship or /commit |
| `auto_format.py` | After Write/Edit | Auto-formatting (ruff/prettier/gofmt) + file logging |
| `session_metrics.py` | On session end | Records session metrics to DB |
| **`session_start.py`** (v1.2) | On session start | Auto-injects state + Memory Block — no manual `/start` needed |
| **`user_prompt_submit.py`** (v1.2) | On user prompt | Detects coding-intent (EN+RU) → nudges if no active task |
| **`keyword_detector.py`** (v1.2) | On agent stop | Catches "I'll implement"/"сейчас напишу" drift phrases → blocks stop |
| **`session_cleanup_check.py`** (v1.2) | On agent stop | Warns about open exploration / review tasks / session timeout |
| **`task_done_verify.py`** (v1.2) | After task_done | Audits AC evidence via 5 rule-based checks (Ralph-mode-lite) |
| **`notify_on_done.py`** (v1.2, optional) | After task_done | Sends webhook to Slack/Discord/Telegram if configured |

Shared helpers live in `scripts/hooks/_common.py` (tausik_path, has_active_task, is_task_done_invocation).

## How It Works

```
You: "add a button to the homepage"

Agent wants to edit index.html
  → task_gate.py checks: is there an active task? No → BLOCKED
  → Agent creates a task via /plan, starts
  → task_gate.py checks again: task exists → ALLOWED

Agent edits index.html
  → auto_format.py: formats the file with prettier
  → auto_format.py: logs "Modified: index.html" to the task
```

## Exit Codes

| Code | Meaning | Behavior |
|------|---------|----------|
| 0 | Success | Action allowed |
| 1 | Warning | Action allowed, warning logged |
| 2 | Block | Action **cancelled**, agent receives the reason |

## What bash_firewall Blocks

- `rm -rf /` and `rm -rf .` — filesystem deletion
- `DROP TABLE`, `DROP DATABASE`, `TRUNCATE TABLE` — data deletion
- `git reset --hard` — loss of local changes
- `git push --force` — overwriting remote history
- `git clean -fd` — deleting untracked files
- `dd if=/dev/zero`, `mkfs.` — disk formatting
- Fork bombs

## Disabling Hooks

For testing or debugging: set the environment variable `TAUSIK_SKIP_HOOKS=1`.

In `.claude/settings.json` hooks are generated automatically during bootstrap.
If you need to disable a specific hook — remove it from the `hooks` section in settings.json.

## What's Next

- **[Workflow](workflow.md)** — how hooks fit into the work cycle
- **[CLI Commands](cli.md)** — managing tasks from the terminal
