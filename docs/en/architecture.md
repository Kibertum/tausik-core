**English** | [Русский](../ru/architecture.md)

# TAUSIK Architecture Reference

## Architecture: CLI -> Service -> Backend

Three layers with clear boundaries. The Service layer contains business logic,
the Backend handles only CRUD and SQL. CLI and MCP are two equal entry points.

```
  Engineer (free-form text)
       |
  AI Agent (Claude Code / Cursor)
       |
  +---------------------------+
  | Skills (SKILL.md)         |  <- instructions for the agent
  +---------------------------+
       |                |
  +---------+    +---------+
  | MCP     |    | CLI     |  <- two entry points
  | (tools) |    | (bash)  |
  +----+----+    +----+----+
       +------+-------+
              |
  +---------------------------+
  | Service Layer             |  <- business logic, QG-0, QG-2
  | project_service.py        |
  | + service_task.py         |
  | + service_knowledge.py    |
  +---------------------------+
              |
  +---------------------------+
  | Backend Layer             |  <- SQLite CRUD, FTS5, metrics
  | project_backend.py        |
  | + backend_queries.py      |
  | + backend_graph.py        |
  | + backend_schema.py       |
  | + backend_migrations.py   |
  +---------------------------+
              |
  +---------------------------+
  | SQLite (WAL mode)         |  <- .tausik/tausik.db
  | 18 tables + FTS5 indexes  |
  +---------------------------+
```

## Key Modules

### Scripts (Business Logic)

| File | Lines | Purpose |
|------|-------|---------|
73 source files in `scripts/` (v1.3). Highlights:

| File | Purpose |
|------|---------|
| `project.py` | CLI entry point, dispatch |
| `project_parser.py` | argparse command tree |
| `project_cli.py` / `_extra.py` / `_ops.py` | CLI handlers (status, task, session, memory, gates, skills, fts, metrics, search, events, explore, audit, run) |
| `project_cli_doctor.py` / `_role.py` / `_stack.py` / `_verify.py` | v1.3 CLI handlers (doctor, roles, stacks, verify) |
| `project_service.py` + `service_*.py` mixins | Business logic: tasks, knowledge, skills, gates, cascade, roles, verification |
| `service_verification.py` | Scoped pytest gate + verify cache (10 min TTL) |
| `service_roles.py` | Hybrid role storage (DB metadata + agents/roles/*.md) |
| `service_stack_ops.py` | Stack scaffold, lint, diff, reset |
| `project_backend.py` + `backend_*.py` | SQLite + FTS5 backend (WAL mode, 18 tables) |
| `backend_session_metrics.py` | Gap-based active-time computation |
| `backend_tier_metrics.py` | call_budget vs call_actual tier metrics |
| `backend_migrations.py` / `_legacy.py` | Schema migrations through v18 |
| `project_config.py` + `default_gates.py` | Config loader, gates config, auto-enable |
| `gate_runner.py` + `gate_stack_dispatch.py` + `gate_test_resolver.py` | Scoped pytest mapping + dispatch |
| `skill_manager.py` + `skill_repos.py` | Skill install/uninstall from repositories |
| `brain_*.py` | Shared Brain (Notion mirror, sync, classifier, registry) |
| `cq_client.py` | Cross-project queue client |
| `doc_extract.py` | markitdown integration |
| `docs_lint.py` | Warning-only stale-version linter |
| `plan_parser.py` | Markdown plan parser for `/run` |
| `model_routing.py` + `notifier.py` | Model selection + webhooks |
| `ide_utils.py` | IDE detection, paths, registry |
| `tausik_utils.py` + `tausik_version.py` + `project_types.py` | Helpers, version, types |

### Bootstrap (Generation)

| File | Lines | Purpose |
|------|-------|---------|
| `bootstrap.py` | ~320 | Orchestration: vendor sync, copy, generate |
| `bootstrap_vendor.py` | ~280 | Download vendor skills from GitHub (tarball) |
| `bootstrap_copy.py` | ~180 | Copy skills, scripts, MCP, references |
| `bootstrap_config.py` | ~70 | Configuration, stack detection |
| `bootstrap_generate.py` | ~300 | Generate settings.json, CLAUDE.md, skill catalog |
| `analyzer.py` | ~330 | Extended stack detection, codebase analysis |

### MCP Server

| File | Purpose |
|------|---------|
| `agents/claude/mcp/project/server.py` | JSON-RPC stdio server |
| `agents/claude/mcp/project/tools.py` | core tool definitions |
| `agents/claude/mcp/project/tools_extra.py` | extended tool definitions (skills, gates, doctor, verify, roles, stacks, brain) |
| `agents/claude/mcp/project/handlers.py` | Dispatch: tool name -> service method |
| `agents/claude/mcp/project/handlers_skill.py` | Skill + maintenance handlers (split) |

Total MCP surface: **96 project tools + 10 brain tools = 106**.

### Cross-IDE Support

Skills, roles, stacks -- shared across IDEs. MCP servers are IDE-specific:
```
agents/
+-- skills/           # 16 built-in + 22 vendor = 38 deployed
+-- roles/            # 5 roles (developer, architect, qa, tech-writer, ui-ux)
+-- stacks/           # Stack guides
+-- overrides/        # IDE-specific overrides (claude/, cursor/, qwen/)
+-- claude/mcp/       # MCP servers (project, codebase-rag)
+-- cursor/mcp/       # MCP servers for Cursor
+-- qwen/ → claude/   # Qwen Code (falls back to Claude MCP)
```

## DB: Tables (Schema v18)

| Table | Purpose |
|-------|---------|
| `meta` | Metadata (schema_version) |
| `epics` | Epics |
| `stories` | Stories (-> epic) |
| `tasks` | Tasks (-> story, scope, defect_of, plan, AC) |
| `sessions` | Sessions (start, end, summary, handoff) |
| `memory` | Project memory (pattern, gotcha, convention, context, dead_end) |
| `decisions` | Architectural decisions |
| `events` | Audit log (gate_bypass, status_changed, claimed) |
| `explorations` | Investigations (time-boxed) |
| `memory_edges` | Graph links between memory/decision (Graphiti) |
| `fts_tasks` | FTS5 full-text index for tasks |
| `fts_memory` | FTS5 index for memory |
| `fts_decisions` | FTS5 index for decisions |
| `task_logs` | Structured task logs (phase, message) |
| `fts_task_logs` | FTS5 index for task logs |
| `roles` | Role registry (hybrid: metadata + agents/roles/{slug}.md) |
| `session_activity` | Per-tool-call timestamps for gap-based active time |
| `verification_runs` | Verify cache: file_hash + timestamp for QG-2 reuse (10 min TTL) |

## Quality Gates

```
project_config.py       -> DEFAULT_GATES (16 gates)
                        -> STACK_GATE_MAP (auto-enable by stack)
                        -> auto_enable_gates_for_stacks()
gate_runner.py          -> run_gates(trigger, files)
                        -> run_command_gate() / run_filesize_gate() / run_tdd_order_gate()
service_task.py         -> _run_quality_gates() (called from task_done)
```

Gates: `pytest`, `ruff`, `mypy`, `bandit`, `filesize`, `tdd_order`, `tsc`, `eslint`,
`go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`.

## Testing

```bash
pytest tests/ -v                    # all tests (2235)
pytest tests/test_tausik_backend.py   # backend CRUD
pytest tests/test_tausik_service.py   # service logic
pytest tests/test_tausik_cli.py       # CLI smoke
pytest tests/test_gates.py          # quality gates + stack auto-enable
pytest tests/test_vendor.py         # vendor skills + persistence
pytest tests/test_graph_memory.py   # graph memory edges
pytest tests/test_mcp_integration.py # MCP handlers
pytest tests/test_senar.py          # SENAR compliance
pytest tests/test_e2e_workflow.py   # E2E workflow
```
