# Environment Rules

**Rules for shell, virtual environments, and Docker.**

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
Full reference: `.claude/references/project-cli.md`

---

## Summary Checklist

- [ ] Git Bash NOT used (PowerShell or WSL)
- [ ] Docker Compose detected → no local stack
- [ ] Project venv: `.venv/` in project root
- [ ] RAG venv: `.rag/venv/` (separate)
- [ ] Both venvs in .gitignore
- [ ] Correct package manager used
