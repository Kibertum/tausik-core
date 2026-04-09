# TAUSIK Architecture Reference

**English** | [Русский](architecture.md)

## Architecture: CLI → Service → Backend

Three layers with clear boundaries. The Service layer contains business logic,
the Backend — only CRUD and SQL. CLI and MCP are two equal entry points.

```
  Engineer (free-form text)
       ↓
  AI Agent (Claude Code / Cursor)
       ↓
  ┌─────────────────────────┐
  │ Skills (SKILL.md)       │  ← instructions for the agent
  └─────────────────────────┘
       ↓                ↓
  ┌─────────┐    ┌─────────┐
  │ MCP     │    │ CLI     │  ← two entry points
  │ (tools) │    │ (bash)  │
  └────┬────┘    └────┬────┘
       └──────┬───────┘
              ↓
  ┌─────────────────────────┐
  │ Service Layer           │  ← business logic, QG-0, QG-2
  │ project_service.py      │
  │ + service_task.py       │
  │ + service_knowledge.py  │
  └─────────────────────────┘
              ↓
  ┌─────────────────────────┐
  │ Backend Layer           │  ← SQLite CRUD, FTS5, metrics
  │ project_backend.py      │
  │ + backend_queries.py    │
  │ + backend_graph.py      │
  │ + backend_schema.py     │
  │ + backend_migrations.py │
  └─────────────────────────┘
              ↓
  ┌─────────────────────────┐
  │ SQLite (WAL mode)       │  ← .tausik/tausik.db
  │ 11 tables + 4 FTS5      │
  └─────────────────────────┘
```

## Key Modules

### Scripts (business logic)

| File | Lines | Purpose |
|------|-------|---------|
| `project.py` | ~120 | CLI entry point, dispatch |
| `project_parser.py` | ~380 | argparse command tree |
| `project_cli.py` | ~345 | CLI handlers (status, task, session, roadmap) |
| `project_cli_extra.py` | ~375 | CLI handlers (memory, gates, skills, fts) |
| `project_cli_ops.py` | ~145 | CLI handlers (metrics, search, events, explore, audit, run) |
| `project_service.py` | ~340 | ProjectService + SessionMixin + HierarchyMixin |
| `service_task.py` | ~375 | TaskMixin: task lifecycle, QG-0, QG-2 |
| `service_knowledge.py` | ~325 | KnowledgeMixin: memory, decisions, graph, explorations |
| `service_skills.py` | ~220 | SkillsMixin: activate, deactivate, list, install |
| `service_gates.py` | ~340 | GatesMixin: QG-0, QG-2, SENAR checklist |
| `service_cascade.py` | ~45 | CascadeMixin: auto-start/close story/epic |
| `project_backend.py` | ~395 | SQLiteBackend: WAL, FTS5, hierarchy + task CRUD |
| `backend_crud.py` | ~230 | BackendCrudMixin: session, decision, memory, meta, events |
| `backend_queries.py` | ~375 | Metrics, roadmap, search, graph traversal |
| `backend_graph.py` | ~110 | Graph memory (edges) + explorations |
| `backend_schema.py` | ~240 | DDL: 11 tables + 4 FTS + triggers + indexes |
| `backend_migrations.py` | ~160 | Migrations v10→v15 + import legacy |
| `backend_migrations_legacy.py` | ~280 | Legacy migrations v2→v9 |
| `project_config.py` | ~350 | Config loader, gates config, auto-enable |
| `gate_runner.py` | ~215 | Quality gates execution |
| `skill_manager.py` | ~360 | Skill install/uninstall from repositories |
| `skill_repos.py` | ~200 | Skill repository management |
| `ide_utils.py` | ~125 | IDE detection, paths, registry |
| `plan_parser.py` | ~125 | Markdown plan parser for /run |
| `tausik_utils.py` | ~50 | Slug validation, timestamps, slugify |
| `project_types.py` | ~40 | TypedDict, constants |
| `tausik_version.py` | ~3 | Version |

### Bootstrap (generation)

| File | Lines | Purpose |
|------|-------|---------|
| `bootstrap.py` | ~320 | Orchestration: vendor sync, copy, generate |
| `bootstrap_vendor.py` | ~280 | Downloading vendor skills from GitHub (tarball) |
| `bootstrap_copy.py` | ~180 | Copying skills, scripts, MCP, references |
| `bootstrap_config.py` | ~70 | Configuration, stack detection |
| `bootstrap_generate.py` | ~300 | Generating settings.json, CLAUDE.md, skill catalog |
| `analyzer.py` | ~330 | Extended stack detection, codebase analysis |

### MCP Server

| File | Purpose |
|------|---------|
| `agents/claude/mcp/project/server.py` | JSON-RPC stdio server |
| `agents/claude/mcp/project/tools.py` | 54 tool definitions (core) |
| `agents/claude/mcp/project/tools_extra.py` | 19 tool definitions (skills, gates, maintenance) |
| `agents/claude/mcp/project/handlers.py` | Dispatch: tool name → service method |
| `agents/claude/mcp/project/handlers_skill.py` | Skill + maintenance handlers (split) |

### Cross-IDE Support

Skills, roles, stacks — shared across IDEs. MCP servers are IDE-specific:
```
agents/
├── skills/           # 33 skills (core + extension + solo)
├── roles/            # 5 roles (developer, architect, qa, tech-writer, ui-ux)
├── stacks/           # Stack guides
├── overrides/        # IDE-specific overrides
├── claude/mcp/       # MCP servers (project, codebase-rag)
└── cursor/mcp/       # MCP servers for Cursor
```

## DB: Tables (Schema v15)

| Table | Purpose |
|-------|---------|
| `meta` | Metadata (schema_version) |
| `epics` | Epics |
| `stories` | Stories (→ epic) |
| `tasks` | Tasks (→ story, scope, defect_of, plan, AC) |
| `sessions` | Sessions (start, end, summary, handoff) |
| `memory` | Project memory (pattern, gotcha, convention, context, dead_end) |
| `decisions` | Architectural decisions |
| `events` | Audit log (gate_bypass, status_changed, claimed) |
| `explorations` | Explorations (time-boxed) |
| `memory_edges` | Graph edges between memory/decision (Graphiti) |
| `fts_tasks` | FTS5 full-text index on tasks |
| `fts_memory` | FTS5 index on memory |
| `fts_decisions` | FTS5 index on decisions |
| `task_logs` | Structured task logs (phase, message) |
| `fts_task_logs` | FTS5 index on task logs |

## Quality Gates

```
project_config.py       → DEFAULT_GATES (15 gates)
                        → STACK_GATE_MAP (auto-enable by stack)
                        → auto_enable_gates_for_stacks()
gate_runner.py          → run_gates(trigger, files)
                        → run_command_gate() / run_filesize_gate()
service_task.py         → _run_quality_gates() (called from task_done)
```

Gates: `pytest`, `ruff`, `mypy`, `bandit`, `filesize`, `tsc`, `eslint`,
`go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`.

## Testing

```bash
pytest tests/ -v                    # all tests (918)
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
