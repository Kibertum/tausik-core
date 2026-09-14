**English** | [Русский](../ru/doctor.md)

# Doctor — Health Check

`doctor` is a single command that checks the moving parts of a TAUSIK install — venv, DB, MCP servers, skills, deployment drift, config, gates, session, and backlog hygiene. It does **not** auto-fix: it tells you what is wrong and how to fix it.

Some checks only run when the thing they check is installed (the Kilo and OpenCode config checks), so the number of lines you see depends on your setup. The table below lists every check that can appear.

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
| **MCP** | Server can start | `python server.py --probe` returns success |
| **Skills** | Deployment | Skills present in `.claude/skills/` (count) |
| **Skills** | Critical skills | core skills `start`, `end`, `task`, `plan`, `checkpoint`, `commit`, `explore`, `review`, `test`, `ship`, `debug` all present |
| **Drift** | Bootstrap freshness | Files in `.claude/` match generators in `harness/`/`bootstrap/`. Drift = stale generated copy. |
| **Config** | Knobs | `session_max_minutes`, `session_warn_threshold_minutes`, `session_idle_threshold_minutes`, `session_capacity_calls`, `verify_cache_ttl_seconds` |
| **Gates** | Registered gates | Stack-detected + universal gates count |
| **Session** | Active vs wall | If session is open: `Xm active / Ym wall` (gap-based) |
| **Backlog** | Epic reachability | Every open task (planning/active/blocked/review) is reachable from an epic. A task with no story shows up in neither `tausik roadmap` nor `task list --epic` — so it drops out of the release scope count silently. WARN, not FAIL: a standalone task is legitimate. Closed tasks do not count. |
| **Backlog** | Deferred AC | No closed task inside a **still-open** epic left an acceptance criterion marked `DEFERRED`. Such a criterion has no owner and no due date, and the epic can close over it. Clear it by finishing the criterion, or by handing it to a task that owns it and recording that: `tausik task log <slug> "AC-N CARRIED BY <owning-slug>"`. Scoped to open epics on purpose — a criterion parked in an epic that shipped long ago is history, not work. |
| **Hooks** | Commit hooks | Tells THREE states of `core.hooksPath` apart, not two. The path resolves a `pre-commit` — OK, and the value is printed. The path is UNSET — also OK, deliberately: [hooks.md](hooks.md) prescribes exactly that for CI runners without mypy, and reddening there would teach the reader to skip the line on every CI box. The path is SET but no `pre-commit` resolves under it — WARN: git treats a hook it cannot find as one that is not there, runs nothing and SAYS nothing, so `memory_route` (block), mypy and the RAG reindex skip every commit while `gates status` still prints the gates `[ON]`. The check PROBES for the hook file and never runs it: a diagnostic that executes what it diagnoses is a side effect. |
| **Hooks** | Enforcement coverage | Per host, the real-time mechanism bootstrap ACTUALLY deployed into its profile — hook commands in `settings.json`, plugins under `plugins/` — counted from disk, never from a table of which rules ought to be enforced where. Measured in session #230: claude and qwen 23 hook commands each, opencode 1 plugin, cursor and kilo none. The gap is NOT a warning: it is declared, and each host's rules file now opens by saying whether the rules below are checks or instructions. The WARN is a CONTRADICTION — a rules file claiming automatic enforcement while its profile holds no mechanism (every file generated before v1.9 carries that claim, and they are preserve-if-exists so bootstrap will not replace them), or a file denying enforcement the profile does have. A file that says nothing either way is not a red: silence is not a false statement. |
| **Session** | Session model | Which model is running the open session, and WHICH SOURCE said so. Resolved as a chain: `TAUSIK_AGENT_MODEL` → host variables (`CLAUDE_MODEL`, `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `CURSOR_MODEL`) → the host's provider (`get_active_model`, which reads the transcript on Claude Code) → absence. Measured in session #231, this had never once succeeded: 0 of 231 sessions carried a model id and 0 of 1560 tasks carried a pin, because the environment was the ONLY source consulted and Claude Code exports none of those variables — so model pinning (RENAR 10.13), per-model cost and per-model metrics were all empty. WARN when the open session has no model, naming `TAUSIK_AGENT_MODEL` as the way to declare one; a second wording covers the session that opened before a source existed. The model is NEVER inferred from the host's name: Claude Code pointed at another endpoint is running that endpoint's model. |
| **Session** | Agent route | How the framework was reached this session: calls through the MCP tools versus calls through the shell, with the MCP share as a percentage. Measured before this line existed (session #233, 4,011 shell commands): 1,216 of 1,530 CLI invocations HAD an MCP twin and used the shell anyway — 79.5% — while `MCP-first` is stated as a hard constraint and nothing counted it. NO THRESHOLD is applied, deliberately: 20.5% of CLI invocations have no MCP twin, chaining (`verify && task done`) cannot be expressed on the MCP surface, and a long multi-line argument is genuinely easier through `"$(cat file)"`. A warning that fired on those would be one the reader learns to skip, and a skipped warning costs the attention the next real one needs. The line reports; the reader judges. |
| **Drift** | CLAUDE.md drift | Sections your `CLAUDE.md` carries under the template's **own** heading still match the template. A heading the file does not carry is customisation, not drift — translating, renaming or dropping a section is a deliberate choice. A missing section still counts as drift when the file otherwise *is* the template's document (more than half its sections present), so a project whose config asks for a directive its `CLAUDE.md` lacks is still caught. The remediation names the diverging sections; it never tells you to re-run bootstrap, which would overwrite hand-written content. |
| **Config** | Trust tier | Distinguishes THREE states, not two. Nothing weakens enforcement — OK. A project-scope key TRIED to weaken it and was dropped on read — WARN, naming the key and the value applied instead. A key a TRUSTED tier (`~/.tausik/config.json`, `$TAUSIK_MANAGED_CONFIG`) holds weaker than the framework default — WARN, naming the tier, the file and the reason recorded beside it. The third state used to print as the first: the resolver measures a candidate against the trusted tiers, so a tier is never weaker than itself, and the OK line read as "nothing is weakened" while the user tier bypassed the signed QG-2 receipt in every project on the machine. WARN and never FAIL — a trusted tier is the operator's word, and doctor owes visibility here, not a verdict. See [config-trust-tiers.md](config-trust-tiers.md). |
| **Config** | Verify-First profile | `auto_verify` is not silently enabling itself on an interactive machine. |
| **IDE** | Kilo / OpenCode config | Present only when that IDE profile is installed: the config parses and its `tausik-project` MCP stanza resolves. |

## Sample Output

```
TAUSIK doctor — health check
========================================
  OK    Python venv               .tausik/venv
  OK    Project DB                .tausik/tausik.db (3136 KB)
  OK    MCP server (project)      .claude/mcp/project/server.py
  OK    Core skills               13 deployed (all critical present)
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
| `WARN Backlog hygiene` | `tausik task move <slug> <story>` for each named task — or create a story for them if they form a coherent group |
| `WARN Commit hooks` | `git config core.hooksPath scripts/hooks` (dev checkout) or `.tausik-lib/scripts/hooks` (consumer project); or `git config --unset core.hooksPath` if the hooks are being switched off on purpose |
| `WARN Enforcement coverage` | The named rules file contradicts its host's profile. Delete that file and re-run `python .tausik-lib/bootstrap/bootstrap.py --ide all` — rules files are preserved when present, so the stale sentence survives a plain re-run |
| `WARN Session model` | Set `TAUSIK_AGENT_MODEL` to the model id actually serving this session, or — if the line says one is available now — close the session and open a new one, since the model is recorded once, at session open |

## Negative — What Doctor Does NOT Do

- It does **not** auto-fix. Each line shows what's wrong; the fix command is yours to run.
- It does **not** validate vendor skill correctness — only presence.
- It does **not** run quality gates (use `tausik gates status` / `tausik verify`).

## What's Next

- **[CLI Commands](cli.md)** — full command reference
- **[Configuration](configuration.md)** — config knobs the doctor checks
- **[Troubleshooting](troubleshooting.md)** — deeper recovery steps
