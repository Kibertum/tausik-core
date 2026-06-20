# Troubleshooting Reference

Machine-readable guide: error → diagnosis → fix.

## Prompt caching not active

Symptom: token cost per session grows faster than expected; the LLM bill shows
almost all input as plain `input_tokens` rather than `cache_read_input_tokens`.
Check with `python scripts/validate_prompt_caching.py --auto` (or pass a JSONL
path). Exit code 2 = API never returns cache fields; exit code 1 =
`cache_creation > 0` but `cache_read = 0` (every turn re-caches the prefix).

| Symptom | Diagnosis | Fix |
|---|---|---|
| `validate_prompt_caching.py` exit=2 (no cache fields) | Current client / endpoint does not request caching | Use the official Claude Code (caching on by default). For third-party wrappers, verify they send `cache_control` on at least system prompt + tools. |
| Exit=1 (creation > 0, reads = 0) | Prefix unstable — something is changing between turns | See the invalidator list below. |
| `cache_read_input_tokens` drops to zero mid-session | `tausik_update_claudemd` rewrote the dynamic CLAUDE.md block | Do not run `update_claudemd` between tool calls; keep it on session boundaries (`/start`, `/checkpoint`, `/end`). |
| Low hit-rate (<50%) even without CLAUDE.md edits | A `SKILL.md` or MCP `tools.py` was edited in the worktree between turns | After editing any agent artifact, restart MCP / IDE — the prior prefix is already invalidated; continuing the session is pointless cache-wise. |
| Want a live hit-rate read | — | Run `python scripts/validate_prompt_caching.py --auto` after a long session. `usage` blocks are already in `~/.claude/projects/<slug>/*.jsonl`. |

See [architecture.md](architecture.md) "Prompt Caching" section for the
cacheable-surface list and which edits rewrite the prefix.

## Stale MCP modules (silent hangs)

Symptom: `tausik_verify` or `tausik_task_done` never returns. CLI works
fine. The MCP server is running stale Python modules — usually because the
user (or bootstrap) edited service code AFTER the IDE opened, and the IDE
never respawned the MCP child. Multiple MCP project servers for the same
project are also a strong signal (each prior IDE window leaks one).

| Symptom | Diagnosis | Fix |
|---|---|---|
| MCP tool hangs > 60 s but CLI of the same op completes instantly | `tausik_self_check` likely shows `drift_detected=true` or `sibling_mcp_count > 0` — stale modules in memory | Restart the IDE so the MCP project server respawns. Until then use `.tausik/tausik` CLI. |
| `/start` warns `⚠ MCP Health` with stale module list | Watched module mtime advanced after MCP startup | Restart IDE; re-run `/start`. |
| `sibling_mcp_count > 0` reported | Multiple MCP project servers on the same project (window leak) | Close stale IDE windows, then `Get-Process python` (Windows) / `pgrep -f mcp/project/server.py` (POSIX) and kill the older PIDs. |
| `tausik_self_check` returns `error: self_check unavailable` | The running MCP server predates this diagnostic (older than v1.4 polish) | Restart IDE so the new server boots; the diagnostic is registered on fresh startups only. |

Companion gotchas in `.tausik/tausik.db`: #77 (verify hang after editing
`service_verification.py`/`gate_runner.py`), #79 (`task_done` hang on
large evidence), #80 (root cause = stale modules + sibling MCP servers).
The Verify-First Contract's 60 s envelope timeout
(`verify_pipeline_timeout_seconds`) catches new servers; stale ones loaded
their code BEFORE that timer was added and ignore it.

## Shared Brain (Notion)

Brain in v1.4 is Notion-backed (no Docker / CouchDB / Meilisearch / Raven anymore — those were the v1.2 architecture and have been removed). The local mirror is a single SQLite file at `~/.tausik-brain/brain.db`.

| Error Pattern | Diagnosis | Fix |
|---|---|---|
| `notion API: unauthorized` / `401` | Missing or wrong Notion integration token | Export `NOTION_TAUSIK_TOKEN=<your token>` (the var name is configurable via `brain.notion_integration_token_env` in `.tausik/config.json`) and re-run `.tausik/tausik brain status` |
| `brain not initialised` | Project never ran the wizard | `.tausik/tausik brain init` — creates Notion databases and writes `.tausik/config.json` entries |
| `404 page_not_found` | Wrong `brain.notion_parent_page_id` or the integration was not invited to that page | Open the parent page in Notion → Connections → invite your integration |
| `sync stalled / cursor stuck` | Local mirror corrupt or stale | `rm ~/.tausik-brain/brain.db` and re-run `.tausik/tausik brain sync --full` |
| Mirror file missing | Never synced | `.tausik/tausik brain sync` (pull from Notion into mirror) |

## RAG (FTS5)

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| `search_code` returns empty | RAG index empty or stale | Reindex via MCP `reindex` tool or restart RAG server |
| RAG DB missing | Never indexed | Run bootstrap: `python bootstrap/bootstrap.py` |
| `reindex` hangs / times out on large monorepo | `mode=full` walks every tracked file; on 50k+ files this can exceed MCP per-tool timeout | Pass `max_seconds=N` (soft limit — partial result with `truncated=true` is returned) or use `mode=incremental` (default; only re-indexes files changed since `last_commit`). v1.4 also writes `[rag] indexed X/Y files, N chunks, ZZs elapsed` to stderr every 100 files so the host renders progress instead of "frozen". |

## CLI & Project

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| `No config found` / `config.json missing` | Project not initialized | `.tausik/tausik init --name "Project"` |
| `Task 'X' blocked by unfinished dependencies` | Task has unresolved deps | `.tausik/tausik task show X` → finish the blockers it lists, then `.tausik/tausik task unblock X` |
| `No active session` | Session not started | `.tausik/tausik session start` |
| `Task 'X' already claimed by agent Y` | Multi-agent conflict | `.tausik/tausik team status` → wait or override |
| `unrecognized arguments` | CLI syntax error | Read [`docs/en/cli.md`](cli.md) for correct syntax |
| `ModuleNotFoundError` in project.py | Wrong Python or missing sys.path | Run with system Python, not venv: `.tausik/tausik` |

## Failed verify-gate → tausik-gate-fixer (auto-helper)

When `tausik verify` or `tausik task done` returns a blocking failure (filesize / ruff / mypy / pytest), invoke the **`tausik-gate-fixer`** sub-agent instead of decoding the stderr by hand. It reads the stderr + `docs/en/troubleshooting.md` + `docs/en/architecture.md`, then returns a 1-3 step JSON fix plan.

```
Agent(
  subagent_type="tausik-gate-fixer",
  prompt="gate_name=ruff; stderr=<copied>; relevant_files=[...]; task_slug=<slug>; goal=<task goal>",
)
```

Response:
```json
{"gate":"ruff","family":"style","plan":[{"step":1,"action":"edit","target":"scripts/foo.py:42","change":"...","why":"..."}],"meta":{...}}
```

**Action vocabulary** (closed set — the agent picks from these, never invents): `edit`, `extract_module`, `add_test`, `move_file`, `delete_dead_code`, `re_run_gate`. Apply the plan, then `.tausik/tausik verify --task <slug>` again. The sub-agent is read-only — it never edits code itself.

## Bootstrap

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| `.claude/` is stale / skills missing | Bootstrap not run after update | `python bootstrap/bootstrap.py` |
| `FileNotFoundError` on skill | Skill not in core/extension list | Edit `.tausik/config.json` → add the skill name under `bootstrap.core_skills` or `bootstrap.extension_skills`, then re-run `python bootstrap/bootstrap.py` |
| `charmap codec can't encode` (Windows) | Unicode in output on non-UTF8 terminal | Set `PYTHONIOENCODING=utf-8` or use `chcp 65001` |

## MCP Servers

| Error Pattern | Diagnosis | Fix Command |
|---|---|---|
| MCP tool not found / unavailable | `.mcp.json` missing or wrong paths | Re-run `python bootstrap/bootstrap.py` to regenerate `.mcp.json` |
| MCP server crashes on start | Wrong Python path in `.mcp.json` | Re-run `python bootstrap/bootstrap.py` to regenerate `.mcp.json` with correct paths |
| `task_done` hangs / times out in VS Code Claude Extension | Heavy gates (pytest, tsc) ran inline, host killed call at the per-tool timeout | v1.4 Verify-First Contract: call `tausik_verify` first (streams progress, host can interrupt), then `tausik_task_done` reads cache and closes in milliseconds. See [Host limits](#host-limits-task_done-ux). |
| `task_done` returns generic timeout error, no traceback | Old MCP server (pre 1.4) swallowed exceptions to single-line text | Update MCP server: `python bootstrap/bootstrap.py` (1.4 prints traceback to stderr). |
| Agent runs heavy gates inline on task close | MCP server bundled in project predates 1.4 (the Verify-First Contract) | Update bootstrap: `python bootstrap/bootstrap.py`. v1.4 splits verify from close — `tausik_verify` streams progress, `tausik_task_done` reads cache. |

## Host limits & `task_done` UX

The TAUSIK MCP servers run inside an IDE host (VS Code Claude Extension, JetBrains, Cursor, Claude Code, etc.). Every host applies a per-tool timeout (~60s in current builds). If `task_done` triggered the heavy verification stack inline, large monorepos would push past the timeout, the host would kill the call, and the agent would see a generic transport error — not a usable failure report.

**Workflow (preferred):**
1. `tausik_verify(task_slug=…)` — runs heavy gates (pytest, tsc, cargo, phpstan, …), streams progress, the user can interrupt cleanly. Result is cached for 10 minutes.
2. `tausik_task_done(slug=…, ac_verified=True, relevant_files=[…])` — reads the cache, closes the task in milliseconds. Returns structured JSON (`stage`, `gate_results`, `blocking_failures`).

**Opt-out (CI / batch runs):** add `{ "task_done": { "auto_verify": true } }` to `.tausik/config.json`. `task_done` will run the heavy gates inline like in 1.3 — fine outside an interactive host where there is no per-tool timeout.

**`tausik_task_done` is the single QG-2 entrypoint.** Earlier docs referenced a `task_done_v2 vs task_done` migration; v1.4 ships only `tausik_task_done` (structured JSON response with `stage`, `gate_results`, `blocking_failures`). It honours the Verify-First Contract — the heavy gates must already have run via `tausik_verify`, the result is cached for 10 minutes, and `task_done` reads that cache.

**Streaming progress (v1.4):** when `task done` runs gates inline (`auto_verify=true` or interactive `tausik task done`), `gate_runner` emits a `run_start` progress event up-front with `total` (gate count) and `max_seconds` (sum of per-gate timeouts) so MCP hosts can render an ETA before pytest blocks the channel. The CLI handler maps this to one stderr line per event:

```
[gates] Running 2 gate(s) (trigger=task-done, max ~125s).
[gates] 1/2 filesize ...
[gates] 1/2 filesize PASS (8 ms)
[gates] 2/2 pytest ...
[gates] 2/2 pytest PASS (1062 ms)
```

Set `TAUSIK_QUIET=1` to suppress these lines (CI / scripted runs). MCP servers receive the same event payload and can surface it as a structured progress message.

## VS Code Claude Extension — full reference (v1.4)

The VS Code Claude Extension is the strictest MCP host for TAUSIK because it (1) imposes a hard per-tool timeout that cannot be configured from inside the tool, (2) does not expose a hooks API, and (3) renders MCP tool results as a single line. v1.4 ships behavior tuned for this host explicitly. This section consolidates the full picture so you don't have to chase it across `host-limits`, `Host limits`, and the streaming-progress note.

### Hooks status

| Hook category | Claude Code (CLI) | Cursor | VS Code Claude Ext. | Qwen Code |
|---|---|---|---|---|
| PreToolUse / PostToolUse / SessionStart / SessionEnd | ✅ Real, enforced | ❌ No hooks API | ❌ No hooks API | ✅ Real, enforced (full parity since v1.4) |
| `task_gate.py` (Rule 9.1) | Hard block | Instruction-only | Instruction-only | Hard block |
| `secret_scan.py` (Rule 10.12) | Warn / strict-block | Instruction-only | Instruction-only | Warn / strict-block |
| `git_push_gate.py` | Hard block | Instruction-only | Instruction-only | Hard block |

Practical implication: the VS Code extension cannot block file writes when there is no active TAUSIK task. The agent *should* honour the rule (it's spelled out in `CLAUDE.md` and the multi-model onboarding block of `AGENTS.md`), but you don't get the safety net. Treat the rules as conventions, not gates, in this host.

### MCP per-tool timeout

The current extension build kills any single MCP tool call that runs longer than ~60 seconds. There is no client-side knob to bump it. Affected tools and the v1.4 mitigation:

| Tool | Pre-1.4 behavior | v1.4 mitigation |
|---|---|---|
| `tausik_task_done` | Ran pytest/tsc/cargo inline → 60s+ on big repos → killed → generic timeout error | **Verify-First Contract**: refuses to close until `tausik_verify` ran. Verify streams stderr progress, the user can stop it, and its result is cached for 10 min. Then `task done` reads cache and finishes in <100ms. Returns structured JSON (`stage`, `gate_results`, `blocking_failures`) instead of a single error string. |
| `codebase-rag.reindex` (full) | Walked every file silently → host killed at 60s | Accepts `max_seconds` soft limit; emits `[rag] indexed X/Y files...` to stderr every 100 files. Default mode is `incremental` — only files changed since `last_commit`. |
| `tausik_verify` | (introduced 1.4) | The intended foreground heavy-work entrypoint. Streams progress; the user sees what's happening; the host doesn't time out as long as we keep emitting bytes within its idle threshold. |

### Recommended workflow

For routine task closure in VS Code Claude Extension:

1. Skill or agent calls `tausik_verify(task_slug=...)` **first**. This is the only place pytest/tsc/etc. are allowed to run inline.
2. The user sees streaming progress and can intervene (Ctrl-C is delivered to the MCP process).
3. On green, `tausik_verify` writes a `verification_runs` row.
4. Skill calls `tausik_task_done(task_slug=..., relevant_files=[...], ac_verified=true)`.
5. `task_done` checks the cache (≤10 min old, same `files_hash`, same gate signature), confirms green, and closes within ~100ms.
6. If the cache lookup fails, `task_done` returns a structured error explaining exactly which gate is missing — *not* a transport timeout.

For CI / batch / non-interactive runs (where there is no per-tool timeout), set `{ "task_done": { "auto_verify": true } }` in `.tausik/config.json` to restore the legacy 1.3 behaviour where `task_done` runs gates inline.

### Diagnostics

Use these to confirm the extension is configured correctly:

| Symptom | Check |
|---|---|
| Skill calls a legacy `task_done` shape | v1.4 ships a single `tausik_task_done`. If the agent's bundled SKILL.md still says "call v2", re-run `python bootstrap/bootstrap.py` so the `.claude/skills/` (and equivalents) reflect the current contract. |
| Verify never returns | Run the same verify command from a regular terminal (`.tausik/tausik verify --task <slug>`) — if it works there but hangs through the extension, the issue is host-side, not TAUSIK. |
| Hooks not firing on `Write` | Expected — VS Code extension has no hooks API. The agent must obey rules without enforcement; consider running task-critical work through Claude Code CLI or Qwen Code if hard blocks matter. |
