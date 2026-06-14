**English** | [Русский](/ru/docs/mcp)

# TAUSIK MCP — Tool Reference (v1.5)

**124 tools** for AI agents (117 project + 7 brain; v1.5 actual count, asserted via `len(TOOLS)` on both servers). The MCP surface covers everything an agent does day-to-day. A few CLI-only commands have no MCP equivalent — they are operator / maintenance verbs that don't belong in an agent loop: `skill rebuild`, `skill bundle`, `fts optimize`, `db prune`, `audit vendors`/`research`, `config set`/`show`, `push-ok`, `run`, `doc extract`/`constants`, `hud`, `suggest-model`, `hygiene archive --confirm`. For the agent's working set, prefer MCP tools over shell calls — they are atomic, return structured data, and keep your context cleaner.

> **Optional `codebase-rag` server** adds 7 tools (search_code, find_symbol, …). It is enabled separately during bootstrap and is NOT part of the main 124 count — total with it is 131 tools.

Two MCP servers live in this project:

- `tausik-project` — project-scoped tools (99): tasks, sessions, knowledge, stacks, roles, gates, skills, exploration, audit, doctor, verify, usage logging.
- `tausik-brain` — cross-project Shared Brain tools (7).

There is also an optional `codebase-rag` server documented at the bottom.

## Verify-First Contract (v1.5)

Heavy quality gates (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeval, hadolint, ansible-lint) live on a dedicated `verify` trigger. The MCP workflow:

```
tausik_task_start(slug=…)        # QG-0
… work on code …
tausik_verify(task_slug=…)        # heavy: subprocess gates → caches green
tausik_task_done(slug=…, ac_verified=True)   # lightweight: cache lookup
```

`tausik_task_done` will refuse to close the task if the verify cache is missing or stale — it returns a structured failure with explicit remediation. Opt-out for CI: set `{"task_done": {"auto_verify": true}}` in `.tausik/config.json` so the heavy gates fire inside `task_done` like in pre-v1.5 releases.

**Terminology:** [Verify / QG glossary](verify-glossary.md) distinguishes *supported opt-out*, *QG bypass* (not available for `task_done`), *verify-cache bypass*, and the pytest **test shim**.

## Status, Health, Metrics

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_health` | Health check: version, DB, tables | — |
| `tausik_self_check` | MCP-server freshness: startup time, watched-module mtime snapshot vs current on-disk mtimes, `drift_detected` flag, stale modules with `delta_seconds`, sibling MCP project server count. Call from `/start` to catch silent-hang precursors (gotchas #77/#79/#80). | — |
| `tausik_status` | Project overview: tasks, session, epics. Optional `compact: true` → one-line JSON (default text unchanged). | `compact` (optional) |
| `tausik_doctor` | 4-group health (venv + DB + MCP + skills + drift) | — |
| `tausik_metrics` | SENAR metrics: Throughput, FPSR, DER, Dead End Rate, Cost/Task | — |
| `tausik_usage_event_log` | Append manual row to `usage_events` (does not update session aggregates) | `tokens_input`, `tokens_output`, `tokens_total`, `cost_usd` |
| `tausik_search` | Full-text search across tasks, memory, decisions | `query` |

## Tasks

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_task_add` | Create task (optionally in a story) | `slug`, `title` |
| `tausik_task_quick` | Quick creation with auto-slug | `title` |
| `tausik_task_start` | Start work (QG-0: requires goal + AC + negative scenario) | `slug` |
| `tausik_task_done` | Complete (QG-2: `ac_verified=true`, scoped pytest, verify cache). Returns structured JSON: `blocking_failures`, per-gate results, cache status. | `slug` |
| `tausik_task_show` | Full task information | `slug` |
| `tausik_task_list` | List tasks with filters (status enum: `planning,active,blocked,review,done`) | — |
| `tausik_task_update` | Update fields (title/goal/AC/scope/notes/stack/complexity/role/tier/call_budget) | `slug` |
| `tausik_task_plan` | Set plan steps | `slug`, `steps[]` |
| `tausik_task_step` | Mark step as completed | `slug`, `step_num` |
| `tausik_task_log` | Append journal entry | `slug`, `message` |
| `tausik_task_logs` | Read structured logs (filter by phase) | `slug` |
| `tausik_reason_step` | RENAR reasoning step (intent\|premise\|action\|verification) | `slug`, `kind`, `content` |
| `tausik_task_replay` | Chronological task timeline (logs + reasoning + events + verification) | `slug` |
| `tausik_task_block` | Block task | `slug` |
| `tausik_task_unblock` | Unblock | `slug` |
| `tausik_task_review` | Move to review | `slug` |
| `tausik_task_delete` | Delete task | `slug` |
| `tausik_task_move` | Move to another story | `slug`, `new_story_slug` |
| `tausik_task_next` | Pick next task by score | — |
| `tausik_task_claim` | Claim task (multi-agent) | `slug`, `agent_id` |
| `tausik_task_unclaim` | Release task | `slug` |

### `tausik_task_done` parameters

- `ac_verified` — **required** for QG-2
- `evidence` — inline AC verification log (replaces a separate `task_log` call)
- `no_knowledge` — confirm no knowledge to capture (suppresses warning)
- `relevant_files[]` — files modified; drives **scoped** pytest gate (basename match → `tests/test_<file>.py`). Empty list with non-empty original → gate skipped (no false-positive on full suite). Verify cache (10 min TTL) skips re-runs with same `files_hash`.

There is **no `--force`** on `task_done` — QG-2 cannot be bypassed. `task_start` does have `--force` to bypass session capacity, with audit trail.

### `tausik_task_done` structured response

`tausik_task_done` returns JSON for agent workflows:
- stage flags (`plan_complete`, `ac_verified`, `gates_passed`)
- per-gate results (`gates[]`)
- `blocking_failures[]` with gate, files, output, and remediation hints
- `warnings[]`, `cache_status`, and final `ok`

Pre-1.4 there was a parallel `tausik_task_done_v2` alias for the structured-JSON variant. **v14b-task-done-rename-drop-v2 consolidated both into the single `tausik_task_done` returning the structured JSON above** — there is no `_v2` suffix. The Verify-First Contract is honoured on every path.

## Sessions

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_session_start` | Start session | — |
| `tausik_session_end` | End session | — |
| `tausik_session_extend` | Extend active-time limit beyond 180 min | — |
| `tausik_session_current` | Current active session | — |
| `tausik_session_list` | List sessions | — |
| `tausik_session_handoff` | Save handoff data | `handoff` (object) |
| `tausik_session_last_handoff` | Get handoff from previous session | — |
| `tausik_session_open` (v1.5) | Compound RPC: session start + status + handoff + active/blocked tasks + self_check in one envelope. Powers `/start` Phase 1. | — |

Session limit is gap-based **active time** (paused after 10-min idle gap), not wall clock. See `session-active-time.md`.

## Hierarchy (Epics and Stories)

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_epic_add` | Create epic | `slug`, `title` |
| `tausik_epic_list` | List epics | — |
| `tausik_epic_done` | Complete epic | `slug` |
| `tausik_epic_delete` | Delete (cascade: stories + tasks) | `slug` |
| `tausik_story_add` | Create story in epic | `epic_slug`, `slug`, `title` |
| `tausik_story_list` | List stories | — |
| `tausik_story_done` | Complete story | `slug` |
| `tausik_story_delete` | Delete (cascade: tasks) | `slug` |
| `tausik_roadmap` | Tree: epic → story → task | — |

## Knowledge

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_memory_add` | Save to project memory | `type`, `title`, `content` |
| `tausik_memory_search` | Full-text search in memory | `query` |
| `tausik_memory_list` | List entries (filter by type) | — |
| `tausik_memory_show` | Show entry by ID | `id` |
| `tausik_memory_delete` | Delete entry | `id` |
| `tausik_memory_block` | Compact markdown: recent decisions + conventions + dead ends (for /start re-injection) | — |
| `tausik_memory_compact` | Aggregate recent task_logs (phases + top words + top files) | — |
| `tausik_memory_archive` (v1.5) | Soft-archive memory rows older than a duration (90d / 12w / 2m / 1y). Dry-run unless `confirm: true`. | `before` (string), `confirm` (bool, optional) |
| `tausik_memory_dedupe` (v1.5) | List near-duplicate memory pairs above a similarity threshold (read-only). | `threshold` (float, optional), `limit` (int, optional) |
| `tausik_decide` | Record an architectural decision | `decision` |
| `tausik_decisions_list` | List decisions | — |

Memory types: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.

## Graph Memory

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_memory_link` | Create edge between nodes | `source_type`, `source_id`, `target_type`, `target_id`, `relation` |
| `tausik_memory_unlink` | Soft-invalidate edge (never deletes) | `edge_id` |
| `tausik_memory_related` | Find related nodes (1–3 hops) | `node_type`, `node_id` |
| `tausik_memory_graph` | List edges with filters | — |

Relation types: `supersedes`, `caused_by`, `relates_to`, `contradicts`.

## Dead Ends and Explorations

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_dead_end` | Document a failed approach | `approach`, `reason` |
| `tausik_explore_start` | Start time-boxed investigation | `title` |
| `tausik_explore_end` | End investigation | — |
| `tausik_explore_current` | Current investigation | — |

## Quality Gates and Verification

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_gates_status` | Status of all gates (by stack) | — |
| `tausik_gates_enable` | Enable gate | `name` |
| `tausik_gates_disable` | Disable gate | `name` |
| `tausik_verify` | v1.5 Verify-First: run heavy gates (pytest, tsc, …) and cache green in `verification_runs`. After that `tausik_task_done` reads the cache and closes instantly. | `task_slug` |

Available gates: `pytest`, `ruff`, `mypy`, `bandit`, `tsc`, `eslint`, `go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`, `filesize`, `tdd_order`. Stack-scoped gates auto-enable based on detected stack; universal gates (`filesize`, `tdd_order`) apply to all stacks.

`tdd_order` is disabled by default. Enable with `tausik_gates_enable name=tdd_order`.

## Stacks

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_stack_list` | List built-in + custom stacks | — |
| `tausik_stack_show` | Resolved stack: gates per language + override info | `stack` |
| `tausik_stack_export` | Export resolved declaration as JSON | `stack` |
| `tausik_stack_diff` | Diff between built-in and user override | `stack` |
| `tausik_stack_reset` | Remove user override at `.tausik/stacks/<stack>/` | `stack` |
| `tausik_stack_lint` | Validate user-override `stack.json` files | — |
| `tausik_stack_scaffold` | Create `.tausik/stacks/<name>/{stack.json,guide.md}` skeleton | `name` |

DEFAULT_STACKS: 25 entries (python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker). Custom stacks via `.tausik/config.json` → `custom_stacks`.

## Roles

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_role_list` | List roles | — |
| `tausik_role_show` | Show role profile | `slug` |
| `tausik_role_create` | Create role (optionally `extends` a base profile) | `slug`, `title` |
| `tausik_role_update` | Update role metadata | `slug` |
| `tausik_role_delete` | Delete role | `slug` |
| `tausik_role_seed` | Bootstrap rows from `harness/roles/*.md` + existing task usage | — |

Role storage is hybrid: SQLite metadata + `harness/roles/{role}.md` profile markdown. Roles on tasks remain free-text.

## Periodic Audit (SENAR Rule 9.5)

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_audit_check` | Check whether audit is overdue | — |
| `tausik_audit_mark` | Mark audit as completed | — |

## Skills

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_skill_list` | List skills: active, vendored, available | — |
| `tausik_skill_install` | Install skill from repo (clone + copy + deps) | `name` |
| `tausik_skill_uninstall` | Uninstall skill completely | `name` |
| `tausik_skill_activate` | Activate installed skill | `name` |
| `tausik_skill_deactivate` | Deactivate skill (keep files) | `name` |
| `tausik_skill_repo_add` | Add TAUSIK-compatible skill repo (third-party URLs need `force`) | `url`, optional `force` |
| `tausik_skill_repo_remove` | Remove skill repo | `name` |
| `tausik_skill_repo_list` | List repos and available skills | — |
| `tausik_skill_catalog` | Discovery: list skills offered by configured/cloned repos (name, category, description) | optional `repo`, optional `as_json` |

## Cross-Project Queue (CQ)

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_cq_publish` | Publish a cross-project event | `payload` |
| `tausik_cq_query` | Query cross-project queue | — |

## Multi-agent and Maintenance

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_team` | Tasks grouped by agent | — |
| `tausik_events` | Audit log (events) | — |
| `tausik_update_claudemd` | Update dynamic section in CLAUDE.md | — |
| `tausik_fts_optimize` | Optimize FTS5 indexes | — |

## Shared Brain (`tausik-brain`, 7 tools)

| Tool | Description | Required Parameters |
|---|---|---|
| `brain_search` | Search the Notion-backed brain (FTS over local mirror) | `query` |
| `brain_get` | Get a brain record by id | `id`, `category` |
| `brain_store_decision` | Store a cross-project decision | `name`, `decision` |
| `brain_store_pattern` | Store a cross-project pattern | `name`, `description` |
| `brain_store_gotcha` | Store a cross-project gotcha | `name`, `description` |
| `brain_draft_artifact` | Dry-run artifact publish (taxonomy + scrub + classifier risk; no Notion write) | `kind` |
| `brain_cache_web` | Cache a web result for token reuse | `name`, `url`, `content` |

The `tausik-brain` MCP server runs config-agnostic at startup and reads registry from `.tausik-brain/` configuration. The total tool count for this server is 7 (verified via `len(TOOLS)` in `harness/claude/mcp/brain/tools.py`).

### Brain config requirements

When `brain.enabled=true` in `.tausik/config.json`, ALL of the following must be set or `tausik_decide` (and other brain-routing operations) will return a `⚠ ... saved LOCALLY ONLY — brain mirror BLOCKED` warning and skip the Notion mirror:

- `brain.database_ids.decisions`, `database_ids.patterns`, `database_ids.gotchas`, `database_ids.web_cache` — all four Notion database UUIDs.
- `brain.notion_integration_token_env` — env var name (default `NOTION_TAUSIK_TOKEN`) that must resolve to a non-empty token via env, `.tausik/.env`, or `brain.notion_integration_token` in config.

`tausik doctor` surfaces validation errors as a `Brain config` warning row. The fastest fix is `tausik brain init` (interactive wizard) or set `brain.enabled=false` to opt out cleanly. After fixing the config, run `tausik brain move --to-brain` to migrate decisions/gotchas/patterns that were saved locally during the misconfiguration window.

## Codebase RAG (separate optional MCP server)

| Tool | Description | Required Parameters |
|---|---|---|
| `search_code` | Search project code via RAG index | `query` |
| `search_knowledge` | Search project knowledge base | `query` |
| `reindex` | Reindex the codebase | `mode` (incremental/full), `max_seconds` (soft limit, full only). v1.5: stderr progress every 100 files; truncated=true on timeout. |
| `rag_status` | RAG index status | — |
| `archive_done` | Archive completed tasks | — |
| `cache_web_result` | Cache web search result for reuse | `query`, `content` |
| `search_web_cache` | Search cached web results | `query` |

These are not part of the main 105 count — they belong to the optional `codebase-rag` server.

## Launching the Tausik MCP Server

The bootstrap step generates IDE-specific MCP launchers under `harness/<ide>/mcp/`. Claude Code reads `.claude/settings.json` (auto-generated). To regenerate IDE assets and MCP wiring, run `python bootstrap/bootstrap.py` from your TAUSIK checkout (or `python .tausik-lib/bootstrap/bootstrap.py` when using the submodule layout). Use **`python bootstrap/bootstrap.py --refresh`** only to rewrite `.tausik/config.json` (e.g. after setting **`TAUSIK_MODEL_PROFILE`**) without copying skills/scripts — it does **not** regenerate `.mcp.json` files.
