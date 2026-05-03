# Scripts

TAUSIK framework modules. Python 3.11+ stdlib only.

## Architecture: CLI → Service → Backend

| Module | Purpose |
|--------|---------|
| `project.py` | Entry point: argparse dispatch |
| `project_parser.py` | Argparse command tree |
| `project_cli.py` | CLI handlers: task, session, epic, story, roadmap |
| `project_cli_extra.py` | CLI handlers: memory, gates, skill, fts, update-claudemd |
| `project_cli_ops.py` | CLI handlers: metrics, search, events, explore, audit, run |
| `project_service.py` | ProjectService + SessionMixin + HierarchyMixin |
| `service_task.py` | TaskMixin: task lifecycle, QG-0, QG-2 |
| `service_knowledge.py` | KnowledgeMixin: memory, decisions, events |
| `service_skills.py` | SkillsMixin: activate, deactivate, list, install |
| `service_gates.py` | GatesMixin: QG-0, QG-2 gate checks, SENAR checklist |
| `service_cascade.py` | CascadeMixin: auto-start/close story/epic |
| `project_backend.py` | SQLiteBackend: hierarchy + task CRUD |
| `backend_crud.py` | BackendCrudMixin: session, decision, memory, meta, events |
| `backend_schema.py` | Schema: 11 tables, 4 FTS5, triggers, indexes |
| `backend_queries.py` | Complex queries: search, metrics, roadmap |
| `backend_graph.py` | Graph memory (edges) + explorations |
| `backend_migrations.py` | Schema migrations v10→v15 + import legacy |
| `backend_migrations_legacy.py` | Legacy migrations v2→v9 |
| `project_config.py` | Config loader, gates config, service factory |
| `project_types.py` | Constants: valid statuses, stacks, complexities |
| `gate_runner.py` | Quality gates execution engine |
| `skill_manager.py` | Skill install/uninstall from repositories |
| `skill_repos.py` | Skill repository management |
| `ide_utils.py` | IDE detection, registry, path helpers |
| `plan_parser.py` | Markdown plan parser for `/run` batch execution |
| `tausik_version.py` | Version: 1.1.0 |
| `tausik_utils.py` | Utilities: utcnow_iso, ServiceError, validators |

## MCP Servers

Located in `agents/{ide}/mcp/`:

| Server | Purpose |
|--------|---------|
| `project/` | Full project management (tasks, sessions, memory, decisions) |
| `codebase-rag/` | Code search via FTS5 |

## Usage

```bash
# Always via .tausik/tausik wrapper
.tausik/tausik status
.tausik/tausik task quick "Fix bug"
.tausik/tausik search "auth"
```

Full CLI reference: `docs/en/cli.md` (or `docs/ru/cli.md`)
