# Troubleshooting Reference

Machine-readable guide: error → diagnosis → fix.

## Docker & Brain

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| `Connection refused :16042` | CouchDB container not running | `.tausik/tausik brain start` |
| `Connection refused :17758` | Meilisearch container not running | `.tausik/tausik brain start` |
| `Connection refused :11221` | Raven gateway not running | `.tausik/tausik brain start` |
| `401 Unauthorized` (CouchDB) | Wrong CouchDB credentials | Check `.claude-project/config.json` → `brain.couchdb_user/couchdb_password` |
| `database_not_found` / `404` on DB | Project DB not created | `.tausik/tausik brain init` |
| `docker: command not found` | Docker not installed | Install Docker Desktop, restart terminal |
| `docker compose` version error | Old Docker Compose v1 | Upgrade to Docker Compose v2 (`docker compose` without hyphen) |

## RAG (FTS5)

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| `search_code` returns empty | RAG index empty or stale | Reindex via MCP `reindex` tool or restart RAG server |
| RAG DB missing | Never indexed | Run bootstrap: `python bootstrap/bootstrap.py` |

## CLI & Project

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| `No config found` / `config.json missing` | Project not initialized | `.tausik/tausik init --name "Project"` |
| `Task 'X' blocked by unfinished dependencies` | Task has unresolved deps | `.tausik/tausik dep list X` → complete deps first |
| `No active session` | Session not started | `.tausik/tausik session start` |
| `Task 'X' already claimed by agent Y` | Multi-agent conflict | `.tausik/tausik team status` → wait or override |
| `unrecognized arguments` | CLI syntax error | Read [`docs/en/cli.md`](cli.md) for correct syntax |
| `ModuleNotFoundError` in project.py | Wrong Python or missing sys.path | Run with system Python, not venv: `.tausik/tausik` |

## Bootstrap

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| `.claude/` is stale / skills missing | Bootstrap not run after update | `python bootstrap/bootstrap.py` |
| `FileNotFoundError` on skill | Skill not in core/extension list | Edit `.claude/.claude-bootstrap.json` → add to `core_skills` or `extension_skills`, re-bootstrap |
| `charmap codec can't encode` (Windows) | Unicode in output on non-UTF8 terminal | Set `PYTHONIOENCODING=utf-8` or use `chcp 65001` |

## MCP Servers

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| MCP tool not found / unavailable | `.mcp.json` missing or wrong paths | Re-run `python bootstrap/bootstrap.py` to regenerate `.mcp.json` |
| `raven_briefing` returns error | Raven not running or wrong project | Check `.tausik/tausik brain health` |
| MCP server crashes on start | Wrong Python path in `.mcp.json` | Re-run `python bootstrap/bootstrap.py` to regenerate `.mcp.json` with correct paths |
