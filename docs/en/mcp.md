**English** | [Русский](../ru/mcp.md)

# TAUSIK MCP — Tool Reference (v1.4)

**97 tools** for AI agents (91 project + 6 brain; v1.4 actual count, asserted via `len(TOOLS)` on both servers). The MCP surface mirrors the CLI 1:1 with zero CLI-only gaps. Prefer MCP tools over shell calls — they are atomic, return structured data, and keep your context cleaner.

> **Optional `codebase-rag` server** adds 7 tools (search_code, find_symbol, …). It is enabled separately during bootstrap and is NOT part of the main 97 count — total with it is 104 tools.

Two MCP servers live in this project:

- `tausik-project` — project-scoped tools (91): tasks, sessions, knowledge, stacks, roles, gates, skills, exploration, audit, doctor, verify.
- `tausik-brain` — cross-project Shared Brain tools (6).

There is also an optional `codebase-rag` server documented at the bottom.

## Verify-First Contract (v1.4)

Heavy quality gates (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeval, hadolint, ansible-lint) live on a dedicated `verify` trigger. The MCP workflow:

```
tausik_task_start(slug=…)        # QG-0
… work on code …
tausik_verify(task_slug=…)        # heavy: subprocess gates → caches green
tausik_task_done(slug=…, ac_verified=True)   # lightweight: cache lookup
```

`tausik_task_done` will refuse to close the task if the verify cache is missing or stale — it returns a structured failure with explicit remediation. Opt-out for CI: set `{"task_done": {"auto_verify": true}}` in `.tausik/config.json` so the heavy gates fire inside `task_done` like in v1.3.

## Status, Health, Metrics

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_health` | Health check: version, DB, tables | — |
| `tausik_status` | Project overview: tasks, session, epics | — |
| `tausik_doctor` | 4-group health (venv + DB + MCP + skills + drift) | — |
| `tausik_metrics` | SENAR metrics: Throughput, FPSR, DER, Dead End Rate, Cost/Task | — |
| `tausik_search` | Full-text search across tasks, memory, decisions | `query` |

## Tasks

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_task_add` | Create task (optionally in a story) | `slug`, `title` |
| `tausik_task_quick` | Quick creation with auto-slug | `title` |
| `tausik_task_start` | Start work (QG-0: requires goal + AC + negative scenario) | `slug` |
| `tausik_task_done` | Complete (QG-2: `ac_verified=true`, scoped pytest, verify cache) | `slug` |
| `tausik_task_done_v2` | Complete with structured JSON response (`blocking_failures`, per-gate results, cache status) | `slug` |
| `tausik_task_show` | Full task information | `slug` |
| `tausik_task_list` | List tasks with filters (status enum: `planning,active,blocked,review,done`) | — |
| `tausik_task_update` | Update fields (title/goal/AC/scope/notes/stack/complexity/role/tier/call_budget) | `slug` |
| `tausik_task_plan` | Set plan steps | `slug`, `steps[]` |
| `tausik_task_step` | Mark step as completed | `slug`, `step_num` |
| `tausik_task_log` | Append journal entry | `slug`, `message` |
| `tausik_task_logs` | Read structured logs (filter by phase) | `slug` |
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

### `tausik_task_done_v2`

**Preferred for QG-2 since 1.3.7.** Uses the same input fields as `tausik_task_done`, but returns structured JSON for agent workflows:
- stage flags (`plan_complete`, `ac_verified`, `gates_passed`)
- per-gate results (`gates[]`)
- `blocking_failures[]` with gate, files, output, and remediation hints
- `warnings[]`, `cache_status`, and final `ok`

Skills (`/ship`, `/task`) call v2 when it's exposed by the MCP server and fall back to v1 (single aggregated error string, 1.4 behaviour) otherwise. Both paths honour the Verify-First Contract.

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
| `tausik_verify` | v1.4 Verify-First: run heavy gates (pytest, tsc, …) and cache green in `verification_runs`. After that `tausik_task_done` reads the cache and closes instantly. | `task_slug` |

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
| `tausik_role_seed` | Bootstrap rows from `agents/roles/*.md` + existing task usage | — |

Role storage is hybrid: SQLite metadata + `agents/roles/{role}.md` profile markdown. Roles on tasks remain free-text.

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
| `tausik_skill_repo_add` | Add TAUSIK-compatible skill repo | `url` |
| `tausik_skill_repo_remove` | Remove skill repo | `name` |
| `tausik_skill_repo_list` | List repos and available skills | — |

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

## Shared Brain (`tausik-brain`, 6 tools)

| Tool | Description | Required Parameters |
|---|---|---|
| `brain_search` | Search the Notion-backed brain (FTS over local mirror) | `query` |
| `brain_get` | Get a brain record by id | `id`, `category` |
| `brain_store_decision` | Store a cross-project decision | `name`, `decision` |
| `brain_store_pattern` | Store a cross-project pattern | `name`, `description` |
| `brain_store_gotcha` | Store a cross-project gotcha | `name`, `description` |
| `brain_cache_web` | Cache a web result for token reuse | `name`, `url`, `content` |

The `tausik-brain` MCP server runs config-agnostic at startup and reads registry from `.tausik-brain/` configuration. The total tool count for this server is 6 (verified via `len(TOOLS)` in `agents/claude/mcp/brain/tools.py`).

## Codebase RAG (separate optional MCP server)

| Tool | Description | Required Parameters |
|---|---|---|
| `search_code` | Search project code via RAG index | `query` |
| `search_knowledge` | Search project knowledge base | `query` |
| `reindex` | Reindex the codebase | `mode` (incremental/full), `max_seconds` (soft limit, full only). v1.4: stderr progress every 100 files; truncated=true on timeout. |
| `rag_status` | RAG index status | — |
| `archive_done` | Archive completed tasks | — |
| `cache_web_result` | Cache web search result for reuse | `query`, `content` |
| `search_web_cache` | Search cached web results | `query` |

These are not part of the main 97 count — they belong to the optional `codebase-rag` server.

## Launching the Tausik MCP Server

The bootstrap step generates IDE-specific MCP launchers under `agents/<ide>/mcp/`. Claude Code reads `.claude/settings.json` (auto-generated). To re-generate, run `python .tausik-lib/bootstrap/bootstrap.py --refresh`.
