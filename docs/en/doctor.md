**English** | [Русский](/ru/docs/doctor)

# Doctor — Health Check

`doctor` is a single command that checks the moving parts of a TAUSIK install — venv, DB, MCP servers, skills, deployment drift, config, gates, session, and backlog hygiene. It does **not** auto-fix: it tells you what is wrong and how to fix it.

Some checks only run when the thing they check is installed (the Kilo and OpenCode config checks, the Brain check), so the number of lines you see depends on your setup. The table below lists every check that can appear.

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
| **Skills** | Critical skills | core skills `start`, `end`, `task`, `plan`, `checkpoint`, `commit`, `explore`, `review`, `test`, `ship`, `debug` all present (plus `/brain` conditional if Notion configured) |
| **Drift** | Bootstrap freshness | Files in `.claude/` match generators in `harness/`/`bootstrap/`. Drift = stale generated copy. |
| **Config** | Knobs | `session_max_minutes`, `session_warn_threshold_minutes`, `session_idle_threshold_minutes`, `session_capacity_calls`, `verify_cache_ttl_seconds` |
| **Gates** | Registered gates | Stack-detected + universal gates count |
| **Session** | Active vs wall | If session is open: `Xm active / Ym wall` (gap-based) |
| **Backlog** | Epic reachability | Every open task (planning/active/blocked/review) is reachable from an epic. A task with no story shows up in neither `tausik roadmap` nor `task list --epic` — so it drops out of the release scope count silently. WARN, not FAIL: a standalone task is legitimate. Closed tasks do not count. |
| **Backlog** | Deferred AC | No closed task inside a **still-open** epic left an acceptance criterion marked `DEFERRED`. Such a criterion has no owner and no due date, and the epic can close over it. Clear it by finishing the criterion, or by handing it to a task that owns it and recording that: `tausik task log <slug> "AC-N CARRIED BY <owning-slug>"`. Scoped to open epics on purpose — a criterion parked in an epic that shipped long ago is history, not work. |
| **Drift** | CLAUDE.md drift | Sections your `CLAUDE.md` carries under the template's **own** heading still match the template. A heading the file does not carry is customisation, not drift — translating, renaming or dropping a section is a deliberate choice. A missing section still counts as drift when the file otherwise *is* the template's document (more than half its sections present), so a project whose config asks for a directive its `CLAUDE.md` lacks is still caught. The remediation names the diverging sections; it never tells you to re-run bootstrap, which would overwrite hand-written content. |
| **Config** | Trust tier | No project-scope config key weakens enforcement. See [config-trust-tiers.md](config-trust-tiers.md). |
| **Config** | Verify-First profile | `auto_verify` is not silently enabling itself on an interactive machine. |
| **IDE** | Kilo / OpenCode config | Present only when that IDE profile is installed: the config parses and its `tausik-project` MCP stanza resolves. |
| **Brain** | Notion config | Present only when Brain is enabled: all four `database_ids` plus a token are set. |

## Sample Output

```
TAUSIK doctor — health check
========================================
  OK    Python venv               .tausik/venv
  OK    Project DB                .tausik/tausik.db (3136 KB)
  OK    MCP server (project)      .claude/mcp/project/server.py
  OK    MCP server (brain)        .claude/mcp/brain/server.py
  OK    Core skills               12 core + brain conditional, 20 vendor opt-in (all critical present)
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
| `WARN Shared Brain` | Only appears when `.tausik/config.json` could not be interpreted — a malformed file, or a `brain` key that is not a mapping (`{"brain": true}`). The brain is treated as OFF, which is its default, so this never fails the check. Fix the config if you do use the Notion brain; ignore it if you do not. |
| `WARN Backlog hygiene` | `tausik task move <slug> <story>` for each named task — or create a story for them if they form a coherent group |

## Negative — What Doctor Does NOT Do

- It does **not** auto-fix. Each line shows what's wrong; the fix command is yours to run.
- It does **not** validate vendor skill correctness — only presence.
- It does **not** test the brain mirror sync (use `tausik brain status`).
- It does **not** run quality gates (use `tausik gates status` / `tausik verify`).

## What's Next

- **[CLI Commands](cli.md)** — full command reference
- **[Configuration](configuration.md)** — config knobs the doctor checks
- **[Troubleshooting](troubleshooting.md)** — deeper recovery steps
