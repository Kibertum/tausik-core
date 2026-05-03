**English** | [Русский](../ru/doctor.md)

# Doctor — Health Check

`doctor` is a single command that runs eight checks across the moving parts of a TAUSIK install (venv / DB / MCP / Skills / Drift / Config / Gates / Session). It does **not** auto-fix — it tells you what is wrong and how to fix it.

## Run It

```bash
.tausik/tausik doctor
```

Or via MCP: `tausik_doctor` (no parameters). The MCP variant returns the same data as a structured object.

## What It Checks

| Group | Check | Pass criteria |
|-------|-------|---------------|
| **venv** | Python virtualenv | `.tausik/venv/` exists and `python -V` runs |
| **venv** | stdlib only | No third-party packages leaked into venv |
| **DB** | SQLite file | `.tausik/tausik.db` exists, openable |
| **DB** | Schema migration | Latest migration applied (matches `backend_migrations.py`) |
| **DB** | FTS5 indexes | All FTS tables present and queryable |
| **MCP** | Project server | `.claude/mcp/project/server.py` exists |
| **MCP** | Brain server | `.claude/mcp/brain/server.py` exists |
| **MCP** | Server can start | `python server.py --probe` returns success |
| **Skills** | Deployment | Skills present in `.claude/skills/` (count) |
| **Skills** | Critical skills | core skills `start`, `end`, `task`, `plan`, `review`, `brain`, `ship`, `checkpoint` all present |
| **Drift** | Bootstrap freshness | Files in `.claude/` match generators in `agents/`/`bootstrap/`. Drift = stale generated copy. |
| **Config** | Knobs | `session_max_minutes`, `session_warn_threshold_minutes`, `session_idle_threshold_minutes`, `session_capacity_minutes`, `verify_cache_ttl_seconds` |
| **Gates** | Registered gates | Stack-detected + universal gates count |
| **Session** | Active vs wall | If session is open: `Xm active / Ym wall` (gap-based) |

## Sample Output

```
TAUSIK doctor — health check
========================================
  OK    Python venv               .tausik/venv
  OK    Project DB                .tausik/tausik.db (3136 KB)
  OK    MCP server (project)      .claude/mcp/project/server.py
  OK    MCP server (brain)        .claude/mcp/brain/server.py
  OK    Core skills               13 core + 25+ vendor (all critical present)
  WARN  Bootstrap drift           1 script(s) differ — restart MCP server or re-bootstrap
  OK    Config knobs              max=180m warn=150m idle=10m capacity=200 cache_ttl=600s
  OK    Quality gates             6 registered
  OK    Session                   10m active / 10m wall
========================================
WARN OK with 1 warning(s).
```

## Status Levels

| Level | Meaning |
|-------|---------|
| `OK` | Check passed |
| `WARN` | Non-blocking — work continues, but fix recommended |
| `FAIL` | Blocking — TAUSIK won't operate correctly until fixed |

The exit code reflects the worst level: `0` for OK/WARN, `1` for FAIL.

## Common Fixes

| Symptom | Fix |
|---------|-----|
| `FAIL Python venv` | `python -m venv .tausik/venv` (or re-run bootstrap) |
| `FAIL Project DB` | Run `.tausik/tausik init` to create the DB |
| `WARN Bootstrap drift` | `python .tausik-lib/bootstrap/bootstrap.py --refresh` and restart the MCP server |
| `FAIL MCP server` | Re-run bootstrap; ensure `.claude/mcp/` was generated |
| `WARN Core skills` | `tausik skill list`; `tausik skill activate <name>` for missing core skills |

## Negative — What Doctor Does NOT Do

- It does **not** auto-fix. Each line shows what's wrong; the fix command is yours to run.
- It does **not** validate vendor skill correctness — only presence.
- It does **not** test the brain mirror sync (use `tausik brain status`).
- It does **not** run quality gates (use `tausik gates status` / `tausik verify`).

## What's Next

- **[CLI Commands](cli.md)** — full command reference
- **[Configuration](configuration.md)** — config knobs the doctor checks
- **[Troubleshooting](troubleshooting.md)** — deeper recovery steps
