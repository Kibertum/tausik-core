# Environment Variables and Shell Rules

> Two scopes in this doc:
> 1. **TAUSIK environment variables** — every `TAUSIK_*` / `CLAUDE_*` / `CURSOR_*` / `WINDSURF_*` / `CODEX_*` / `QWEN_*` / `ANTHROPIC_*` / `OPENAI_*` / `NOTION_*` knob that the code actually reads. Use them to override behaviour without editing config.
> 2. **Shell rules** — shells / virtual envs / Docker on Windows / POSIX, kept from the original `environment.md`.

---

## TAUSIK Environment Variables

Source of truth: anywhere the code calls `os.getenv` / `os.environ` in `scripts/`. The list below is exhaustive as of v1.4.0.

### Workflow control

| Variable | Effect | Notes |
|---|---|---|
| `TAUSIK_SKIP_HOOKS=1` | Bypasses ALL TAUSIK hooks (task_gate, bash_firewall, secret_scan, push_gate, etc.). Each hook also honours its own narrower switch. | Use for debugging hook behaviour. Never in CI. |
| `TAUSIK_HOOK_FAIL_SECURE=1` | When a hook errors (not blocks), treat the failure as a block. Default is fail-open (errors warn). | Set in security-sensitive CI environments. |
| `TAUSIK_QUIET=1` | Suppresses `[gates]` / `[rag]` progress lines on stderr. | CI / scripted runs. |
| `TAUSIK_VERIFY_FULL=1` | Forces `tausik verify` to run the full pytest suite (drops the `-m 'not slow'` filter). | Use before release; baseline 12 min on the TAUSIK repo. |
| `TAUSIK_SCOPED_SKIP__<gate>=1` | Skips one named gate for the current `verify` / `task_done` run (e.g. `TAUSIK_SCOPED_SKIP__pytest=1`). | Narrow opt-out; documented per gate. |
| `TAUSIK_DISABLE_SESSION_METRICS=1` | SessionEnd hook does not write `session_usage_metrics`. | Use when running tests that simulate sessions. |
| `TAUSIK_DISABLE_TASK_RECOMMENDATION=1` | Suppresses the per-task model-recommendation banner on `task_start`. | CI / sandboxes that don't tolerate writes under `.tausik/`. |
| `TAUSIK_OUTPUT_TRUNCATION_THRESHOLD=<int>` | Per-tool stdout line count above which the `tool_output_truncation_nudge.py` hook coaches the agent to narrow scope. Default 250. | Tunable per project via `.tausik/config.json::tool_output_truncation_threshold`. |
| `TAUSIK_SECRET_SCAN_STRICT=1` | `secret_scan.py` blocks (rather than warns) on likely-secret writes. | Set in shared / production environments. SENAR Rule 10.12. |

### Push-ticket and memory-write switches

| Variable | Effect |
|---|---|
| `TAUSIK_SKIP_PUSH_HOOK=1` | `git_push_gate.py` becomes a no-op (debugging only). |
| `TAUSIK_PUSH_TICKET_PATH=<abs path>` | Override the default `.tausik/.push_ticket.json` location. Used by the test suite. |
| `TAUSIK_ALLOW_PUSH=1` | **No-op since v1.4** — the env-bypass path was removed (replaced by the single-use ticket file). Setting it does nothing; the gate now requires `tausik push-ok` to write a ticket. |
| `TAUSIK_SKIP_MEMORY_HOOK=1` | Skips `memory_pretool_block.py` for a single tool call (rarely needed; safer to use `confirm: cross-project` in the prompt). |
| `TAUSIK_BRAIN_HOOK_DEBUG=1` | Brain hooks log to stderr in addition to silent operation. |
| `TAUSIK_E2E=1` | End-to-end test marker; some hooks emit deterministic output when set. |

### Project + IDE detection

These are typically set by the IDE host, not by the user.

| Variable | Effect |
|---|---|
| `TAUSIK_DIR` | Override the discovery of `.tausik/` (default: walk parents of CWD). |
| `TAUSIK_PROJECT_DIR` | Override the project root (default: parent of `.tausik/`). |
| `TAUSIK_PROJECT_NAME` | Override the project name shown in CLAUDE.md and `tausik status`. |
| `TAUSIK_MANIFEST` | Path to an alternative bootstrap manifest (advanced; testing). |
| `TAUSIK_BRAIN_REGISTRY` | Override `~/.tausik-brain/projects/` registry root. |
| `CLAUDE_PROJECT_DIR` | Set by Claude Code; TAUSIK reads it for project detection. |
| `CLAUDE_PLUGIN_DATA` | Set by Claude Code plugin host. |
| `CLAUDE_CODE_ENTRYPOINT` / `CLAUDE_CODE_SSE_PORT` | Internal Claude Code wiring; informational only. |
| `CURSOR_DIR` / `CURSOR_TRACE_DIR` / `CURSOR_TRACE_ID` | Set by Cursor; used by `ide_utils.py` for IDE detection. |
| `WINDSURF_DIR` / `WINDSURF_SESSION` | Set by Windsurf. |
| `CODEX_HOME` / `CODEX_SANDBOX_DIR` | Set by Codex / OpenCode-style agents. |
| `QWEN_CODE` / `QWEN_HOME` | Set by Qwen Code. |

### Model selection

The skill profile detector reads these in precedence order (`TAUSIK_MODEL_PROFILE` > host-specific > `TAUSIK_MODEL`).

| Variable | Effect |
|---|---|
| `TAUSIK_IDE` / `TAUSIK_IDE_PROFILE` | Force the IDE profile (claude / cursor / qwen / codex). |
| `TAUSIK_MODEL` / `TAUSIK_MODEL_PROFILE` | Force the model profile slug (opus / sonnet / haiku / gpt-4 / gpt-5 / gpt-5-5 / qwen). |
| `TAUSIK_AGENT_MODEL` / `TAUSIK_AGENT_MODEL_VERSION` | Logged into `usage_events` rows when the host doesn't report the active model. |
| `CLAUDE_MODEL` / `CLAUDE_CODE_MODEL` | Read when the host is Claude Code. |
| `CURSOR_MODEL` | Read when the host is Cursor. |
| `ANTHROPIC_MODEL` / `OPENAI_MODEL` / `OPENAI_API_MODEL` / `QWEN_MODEL` | Provider-flavoured model envs; used as fallbacks by the detector. |

### Brain / Notion

| Variable | Effect |
|---|---|
| `NOTION_TAUSIK_TOKEN` | Notion integration token (default name; override via `brain.notion_integration_token_env`). |
| `NOTION_TOKEN` | Generic fallback if `NOTION_TAUSIK_TOKEN` is unset. |
| `NOTION_RICH_TEXT_CHUNK` | Override the rich-text chunk size used by the Notion writer (default 1800). |

---

## Windows Shell

### CRITICAL: Do NOT use Git Bash!

Git Bash on Windows causes these problems:
- Breaks heredoc syntax
- Breaks redirects (`>`, `>>`)
- Creates junk `tmpclaude-*` files
- Path translation issues (`/c/` vs `C:\`)

### Recommended Shells

| Task | Shell |
|------|-------|
| Simple commands (git, npm, docker) | PowerShell or cmd |
| Complex bash scripts | WSL: `wsl bash -c "command"` |
| File creation/editing | Write/Edit tools (NOT echo/cat) |

### PowerShell Syntax

```powershell
# Run command
npm run build

# Chain commands (both must succeed)
npm install; if ($?) { npm run build }

# Environment variables
$env:NODE_ENV = "production"; npm run build

# Multi-line commands
@"
Line 1
Line 2
"@ | Out-File -FilePath "file.txt"

# Run in specific directory
Push-Location "path/to/dir"; npm install; Pop-Location
```

### CRITICAL: /dev/null Does NOT Exist on Windows!

`/dev/null` is Unix-only. Using `>/dev/null`, `2>/dev/null`, or `&>/dev/null` creates a literal `nul` file.

**NEVER use:** `> /dev/null`, `2>/dev/null`, `&> /dev/null`
**Use instead:**
- PowerShell: `command 2>$null` or `command | Out-Null`
- Or simply omit the redirect — let output appear

### Path Separators on Windows

| Context | Separator | Example |
|---------|-----------|---------|
| Python arguments | `/` OK | `.tausik/tausik` |
| PowerShell commands | `\` preferred | `.rag\venv\Scripts\python` |
| JSON/config files | `/` always | `".claude/mcp/codebase-rag/server.py"` |
| Code strings | `/` (escape-safe) | `"src/utils/helper.ts"` |

**Rule:** Forward slashes `/` in Python/code/config. Backslashes `\` in PowerShell/cmd shell commands.

### WSL for Complex Bash

```powershell
# Single command
wsl bash -c "echo 'hello' > file.txt"

# Multi-line script
wsl bash -c "
cd /mnt/c/project
npm install
npm run build
"

# With heredoc
wsl bash -c 'cat <<EOF > config.json
{
  "key": "value"
}
EOF'
```

---

## Docker Compose Detection

### When docker-compose.yml exists

**DO NOT set up local stack!**

If project has `docker-compose.yml` or `compose.yaml`:
1. Stack runs in containers
2. No need for local database installation
3. No need for local service setup
4. Use `docker compose up -d` to start

### Detection in /init

```yaml
# If found: docker-compose.yml, compose.yaml, docker-compose.*.yml
Stack: Docker Compose (no local setup needed)

Commands:
  start: docker compose up -d
  stop: docker compose down
  logs: docker compose logs -f
  rebuild: docker compose up -d --build
```

### Project with Docker

```
project/
├── docker-compose.yml      # <- Stack is here
├── Dockerfile
├── .env                    # Environment for Docker
└── src/                    # Code only, deps in container
```

---

## Python Virtual Environments

### Naming Convention

| Location | Purpose | Name |
|----------|---------|------|
| Project root | Project dependencies | `.venv` |
| `.rag/` | RAG indexer only | `.rag/venv` |

### CRITICAL: Separate venvs!

```
project/
├── .venv/              # Project venv (Python deps)
│   └── ...
├── .rag/
│   └── venv/           # RAG venv (mcp, httpx)
│       └── ...
└── requirements.txt    # Project requirements
```

**Why separate:**
- RAG uses specific versions (mcp, httpx)
- Project may have conflicting deps
- RAG venv is managed by framework
- Project venv is managed by developer

### .gitignore Required Entries

```gitignore
# Virtual environments
.venv/
venv/
.rag/venv/

# Python cache
__pycache__/
*.pyc
*.pyo
.pytest_cache/
```

### Activation Commands

```powershell
# Windows PowerShell - Project venv
.\.venv\Scripts\Activate.ps1

# Windows PowerShell - RAG venv
.\.rag\venv\Scripts\Activate.ps1

# Windows cmd - Project venv
.venv\Scripts\activate.bat

# Unix/WSL - Project venv
source .venv/bin/activate

# Unix/WSL - RAG venv
source .rag/venv/bin/activate
```

### Creating venvs

```powershell
# Project venv (in project root)
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# RAG venv (managed by /init)
python -m venv .rag/venv
.\.rag\venv\Scripts\pip install mcp httpx
```

### Which Python to Use

| Script | Python | Why |
|--------|--------|-----|
| `.claude/scripts/project.py` | `python` (system) | stdlib only |
| `.claude/mcp/codebase-rag/indexer.py` | `.rag/venv` Python | needs httpx |
| `.claude/mcp/codebase-rag/server.py` | `.rag/venv` Python | needs mcp, httpx |
| `.claude/scripts/pdf_parser.py` | `.rag/venv` Python | needs PyMuPDF |
| Project scripts (`src/`, `scripts/`) | `.venv` Python | project deps |

**Rule:** Check imports before running. Non-stdlib imports → use appropriate venv Python.

**Windows examples:**
```powershell
python .claude\scripts\project.py status              # no venv needed
.rag\venv\Scripts\python .claude\mcp\codebase-rag\indexer.py  # RAG venv
.venv\Scripts\python scripts\my_script.py              # project venv
```

---

## Node.js Projects

### Package Manager Detection

| File | Manager |
|------|---------|
| `pnpm-lock.yaml` | pnpm |
| `yarn.lock` | yarn |
| `package-lock.json` | npm |
| `bun.lockb` | bun |

### Use Detected Manager

```powershell
# If pnpm-lock.yaml exists
pnpm install
pnpm run dev

# If yarn.lock exists
yarn install
yarn dev

# If package-lock.json exists
npm install
npm run dev
```

### node_modules in .gitignore

Always ensure:
```gitignore
node_modules/
```

---

## Project Database

**NEVER** access the project database directly (raw CouchDB queries, import sqlite3).
**ALWAYS** use the CLI:
```bash
.tausik/tausik <command>
```
Full reference: [`docs/en/cli.md`](cli.md)

---

## Summary Checklist

- [ ] Git Bash NOT used (PowerShell or WSL)
- [ ] Docker Compose detected → no local stack
- [ ] Project venv: `.venv/` in project root
- [ ] RAG venv: `.rag/venv/` (separate)
- [ ] Both venvs in .gitignore
- [ ] Correct package manager used
