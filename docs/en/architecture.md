**English** | [Русский](/ru/docs/architecture)

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
       v                v
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
  | 27 tables + 8 FTS5 indexes|
  +---------------------------+
```

## Key Modules

### Scripts (Business Logic)

Modules in `scripts/`, each <=500 lines (`filesize` gate; raised from 400 as an
interim measure by decision #190, because the tighter cap was deforming the
architecture rather than improving it). Line count is not the only size control:
the `class_surface` gate separately caps a class's composed public surface after
inheritance, which a per-file cap structurally cannot see. Highlights:

| File | Purpose |
|------|---------|
| `project.py` | CLI entry point, dispatch |
| `project_parser.py` | argparse command tree |
| `project_cli.py` / `_extra.py` / `_ops.py` | CLI handlers (status, task, session, memory, gates, skills, fts, metrics, search, events, explore, audit, run) |
| `project_cli_doctor.py` / `_role.py` / `_stack.py` / `_verify.py` | CLI handlers (doctor, roles, stacks, verify) |
| `project_service.py` + `service_*.py` mixins | Business logic: tasks, knowledge, skills, gates, cascade, roles, verification |
| `service_verification.py` | Scoped pytest gate + verify cache (10 min TTL) |
| `service_roles.py` | Hybrid role storage (DB metadata + harness/roles/*.md) |
| `service_stack_ops.py` | Stack scaffold, lint, diff, reset |
| `project_backend.py` + `backend_*.py` | SQLite + FTS5 backend (WAL mode, 27 tables + 8 FTS5 indexes) |
| `backend_session_metrics.py` | Gap-based active-time computation |
| `backend_tier_metrics.py` | call_budget vs call_actual tier metrics |
| `backend_migrations.py` / `_legacy.py` | Schema migrations through v27 |
| `project_config.py` + `default_gates.py` | Config loader, gates config, auto-enable |
| `gate_runner.py` + `gate_stack_dispatch.py` + `gate_test_resolver.py` | Scoped pytest mapping + dispatch |
| `skill_manager.py` + `skill_repos.py` | Skill install/uninstall from repositories |
| `brain_*.py` | Shared Brain (Notion mirror, sync, classifier, registry) |
| `cq_client.py` | Cross-project queue client |
| `doc_extract.py` | markitdown integration |
| `docs_lint.py` | Warning-only stale-version linter |
| `plan_parser.py` | Markdown plan parser for `/run` |
| `model_routing.py` | Model selection helper |
| `ide_utils.py` | IDE detection, paths, registry |
| `tausik_utils.py` + `tausik_version.py` + `project_types.py` | Helpers, version, types |
| `gen_doc_constants.py` + `mcp_tool_counts.py` | Generate `docs/_generated/constants.json` (v1.5) |
| `audit_orphan_files.py` / `audit_stale_docs.py` / `audit_unused_python.py` / `audit_pytest_dedupe.py` | Static audit reports (review-only, v1.5) |
| `project_cli_hygiene.py` | `tausik hygiene archive` (read-only project hygiene, v1.5) |
| `hooks/check_docs.py` | Pre-commit / CI wrapper for doc-constants drift (v1.5) |

### Bootstrap (Generation)

| File | Lines | Purpose |
|------|-------|---------|
| `bootstrap.py` | ~320 | Orchestration: vendor sync, copy, generate |
| `bootstrap_vendor.py` | ~280 | Download vendor skills from GitHub (tarball) |
| `bootstrap_copy.py` | ~180 | Copy skills, scripts, MCP into `.claude/` |
| `bootstrap_config.py` | ~70 | Configuration, stack detection |
| `bootstrap_generate.py` | ~300 | Generate settings.json, CLAUDE.md, skill catalog |
| `analyzer.py` | ~330 | Extended stack detection, codebase analysis |

### MCP Server

| File | Purpose |
|------|---------|
| `harness/claude/mcp/project/server.py` | JSON-RPC stdio server |
| `harness/claude/mcp/project/tools.py` | core tool definitions |
| `harness/claude/mcp/project/tools_extra.py` | extended tool definitions (skills, gates, doctor, verify, roles, stacks, brain) |
| `harness/claude/mcp/project/handlers.py` | Dispatch only: tool-call counter, `handle_tool`, merge of the per-domain tables |
| `harness/claude/mcp/project/handlers_<domain>.py` | Handlers by domain: `task`, `session`, `status`, `knowledge`, `hierarchy`, `stack`, `role`, `verification`, `cq`, `skill`, `spec`, `adapt`. Each module exports `<DOMAIN>_HANDLERS`; `handlers.py` merges them into `_DISPATCH` |
| `harness/claude/mcp/project/handlers_render.py` | Shared list rendering (`render_list`) — an empty result must read as "nothing here", not as an empty string |

Total MCP surface: **117 project tools + 7 brain tools = 124** (optional `codebase-rag` adds 7 more; not part of the main count).

### Contextual chunk headers (codebase-rag)

A chunk cut out of a file stops carrying what the file was about, so a query
phrased in the document's terms cannot reach a passage phrased in its own. Each
indexed chunk therefore carries a short header built by
`harness/claude/mcp/codebase-rag/rag_context.py`: path words, the symbol it
defines — or the one it sits inside, for a continuation chunk — and the file's
own summary line.

This is contextual retrieval with the model taken out. The published technique
asks an LLM to write a sentence of context per chunk; here the header comes from
metadata the indexer already has, so the same input yields the same bytes and
indexing stays reproducible and offline.

The header lives in its own indexed column (`rag_chunks.context_prefix`), never
in the chunk's content: a word present only in the header still matches, and
still does not appear in what search returns. An index built before v1.8 grows
into the layout on first open — the column is added and the FTS table rebuilt
from the chunks, which are the source of truth.

### Cross-IDE Support

Skills, roles, stacks -- shared across IDEs. So are the MCP servers: `harness/claude/mcp/`
is the single canonical tree, and `copy_mcp` hands it to every IDE that has none of its
own (all of them, today). A per-IDE copy would be a mirror waiting to drift — one used to
exist under `harness/cursor/` and was deleted in v1.7.0.
```
harness/
+-- skills/           # 13 core auto-deployed + brain conditional + 20 in skills-official/ (opt-in via --include-official)
+-- roles/            # 6 roles (architect, developer, devops, qa, tech-writer, ui-ux)
+-- stacks/           # Stack guides
+-- overrides/        # IDE-specific overrides (claude/, cursor/, qwen/)
+-- claude/mcp/       # MCP servers (project, brain, codebase-rag) — canonical for ALL IDEs
+-- opencode/plugins/ # QG-0 enforcement plugin for OpenCode (tool.execute.before)
```

#### Runtime (IDE) × Model — two orthogonal axes (Decision #119)

TAUSIK separates *where* it runs from *which model* answers:

| Axis | What it controls | `bootstrap --ide` target | Active-model detection |
|------|------------------|--------------------------|------------------------|
| **claude** | Claude Code (VSCode/CLI) | `.claude/` + `.mcp.json` | JSONL transcript (`model` field) |
| **cursor** | Cursor | `.cursor/` + `.cursor/mcp.json` | — |
| **qwen** | Qwen Code | `.qwen/settings.json` | — |
| **kilo** | Kilo Code (addon + CLI) | `.kilo/kilo.jsonc` **and** `.kilocode/mcp.json` | `KILO_MODEL` env / `.kilo` config |
| **opencode** | OpenCode (SST) | `opencode.json` + `.opencode/plugins/` | — |

The **model axis** is data, not code: `scripts/model_profiles.py` maps vendor
families (`claude`, `glm`/z.ai) × capability ranks → concrete model ids,
overridable in `.tausik/config.json` `model_profiles.families`. The routing
matrix emits an abstract rank; the active family resolves it to a real model —
so a z.ai GLM session routes to GLM models with no code change. See
[Kilo + z.ai](kilo-zai.md).

## DB: Tables (Schema v37)

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
| `roles` | Role registry (hybrid: metadata + harness/roles/{slug}.md) |
| `session_activity` | Per-tool-call timestamps for gap-based active time |
| `verification_runs` | Verify cache: file_hash + timestamp for QG-2 reuse (10 min TTL) |

## Quality Gates

```
gate_registry.py        -> GATE_REGISTRY: the one declaration per built-in gate
                        -> GateSpec(name, phase, default_config, impl)
                        -> phase: scoped | post_scope
default_gates.py        -> DEFAULT_GATES = universal (from registry)
                                         ∪ stack-scoped (from stack_registry)
                                         ∪ post-scope (from registry)
gate_runner.py          -> run_gates(trigger, files)   [scoped phase only]
                        -> dispatch via GATE_REGISTRY[name].impl,
                           unknown name -> run_command_gate()
gate_post_scope.py      -> run_post_scope_gates()      [post_scope phase]
                        -> verify_first, changelog + one gate_runs row each
service_task.py         -> _run_quality_gates() (called from task_done)
```

Adding a built-in gate is one `GateSpec`. Before `gate-registry-single-source`
it meant four edits, and the two post-scope gates lived in only one of the four:
`gates status` did not list them, `gates enable/disable` could not reach them,
and they wrote no `gate_runs` row — so nothing could prove a QG-2 gate had run.

**Scoped gates** — `(gate_config, files) -> (passed, output)`, run over the
task's declared scope. Universal (always on): `filesize`, `class_surface`,
`tdd_order`, `ruff`, `mypy`, `bandit`, `bootstrap_drift`, `memory_route`,
`renar_drift_schema`, `renar_drift_provenance`.

`class_surface` is the one exception to "run over the declared scope": it ignores
the file list and measures the **whole repo** (~0.65s). A class grows past its cap
through its *bases*, so a scoped run would never see it — the same blindness that
let a module reach 406 lines without blocking anyone. It caps a class's composed
public surface after inheritance, which the per-file `filesize` cap structurally
cannot see: a god-object built from mixins keeps every file under the line cap.
The two **complement** each other — "this class does too much" and "this file is
too long to read" are different defects. Counts are a **lower bound** (AST, never
`import`, so a gate can measure a branch nobody has read yet), and known oversized
classes sit behind a ratchet baseline in `tausik/gates.json` that may only shrink.

**Post-scope gates** — take the close context and edit the QG-2 report:
`verify_first` (a fresh signed verify green must exist) and `changelog`
(convention #275). `get_gates_for_trigger` excludes them, so `run_gates` never
calls one with the wrong signature.

Stack-scoped gates: `pytest`, `tsc`, `eslint`, `js-test`, `go-vet`, `go-test`, `golangci-lint`,
`cargo-check`, `cargo-test`, `clippy`, `phpstan`, `phpcs`, `phpunit`, `javac`, `ktlint`,
`ansible-lint`, `terraform-validate`, `helm-lint`, `kubeconform`, `hadolint`.

## RENAR adoption — advisory-first ("lite")

TAUSIK is a lightweight, zero-dependency framework, so it adopts [RENAR](https://renar.tech)
(reasoning/governance standard) **advisory-first** rather than as heavyweight mandatory
ceremony. Adoption climbs a ladder with explicit entry conditions per rung (Decision #115):

| Rung | What | Status |
|---|---|---|
| 1. Artifacts | SPEC / ADAPT / conformance embedded in the SQLite substrate + one-way `renar/` export | done (RENAR-1) |
| 2. Advisory signals | QG-0 surfaces a **non-blocking** nudge when a high-stakes task (tier `substantial`/`deep`, or `complex`) starts with no linked SPEC and no ADAPT — `gate_qg0_renar.renar_qg0_advisory`, toggle `renar.qg0_advisory` (default on) | done (1.5) |
| 3. Evidence-based hard-gate | promote a specific advisory to **blocking** only when a real defect traces to its absence (per the #91 coherence audit) | 2.0 |
| 4. RENAR-2 signed/immutable ADAPT | sign ADAPT (ed25519) → `tz_immutable=true` + delta-ADAPT — **irreversible, user-directed only** | 2.0 |

The philosophy: RENAR strengthens SENAR by making interpretation **visible** at the natural
gate (QG-0), while keeping the agent unblocked — fail-soft on advisory, fail-closed only on
proven gates. This is a deliberate lightweight-adoption policy, not "unfinished RENAR".

## Orchestrator-worker (model auto-switch via sub-agents)

The main session is the **coordinator** (planning, AC, review). A task of
complexity ≤ medium can be **delegated** to a **worker sub-agent** spawned via
the Agent tool with `model=recommended` — the only programmatic model-selection
Claude Code exposes (Anthropic orchestrator-workers pattern). TAUSIK provides
the delegation **scaffolding/state**; the agent performs the actual spawn.

| Step | Command / mechanism |
|---|---|
| Delegate | `tausik task delegate <slug>` — records {recommended model, parent session} in the `meta` kv (no schema migration). **complex tasks are refused** (they stay with the coordinator). |
| Handoff contract | `tausik task handoff <slug>` — deterministic JSON {slug, goal, acceptance_criteria, scope, scope_exclude, model, skills}; the trimmed `WORKER_SKILLS` profile (no plan/explore/brain). The orchestrator passes it to the Agent tool; the worker echoes it back (round-trip identity). |
| In-session recognition | `task start` on a delegated task surfaces **worker mode** (operating contract) and suppresses the orchestrator-only model-recommendation banner. |
| Scope hard-gate | the worker is scope-bounded — `scope_write_gate` blocks edits outside `scope_paths`, and a delegated task with **no** scope is blocked until it declares one (no legacy fail-open for workers). |
| Summary-back | `tausik task summary-back <slug> "<summary>" [--gates …]` — the worker returns a structured result (stored in `meta`, surfaced in `task show`) so the coordinator picks it up **without** the worker transcript. |

Delegation state is CLI-first (no MCP surface, to avoid doc-count drift) and
lives entirely in the `meta` table (`delegation:<slug>`, `worker_summary:<slug>`).

## Hooks (anti-drift, see [hooks.md](hooks.md))

All hook files under `scripts/hooks/` are registered via `bootstrap/bootstrap_generate.py` (Claude Code) and `bootstrap/bootstrap_qwen.py` (Qwen Code). Hook scripts are non-blocking (exit 0); errors go to stderr. Shared helpers live in `scripts/hooks/_common.py`.

Brain hooks share helpers in `scripts/brain_hook_utils.py` — a single mirror-lookup + TTL-semantics implementation. Brain-connection setup is in `scripts/brain_runtime.py`: `open_brain_deps() -> (conn, client, cfg)`. The `/brain` skill provides the conversational UI.

## Memory Aggregates

`service_knowledge_aggregates.py` holds pure functions for memory re-injection:

- `build_memory_block(be, ...)` — compact markdown (decisions + conventions + dead ends), ≤50 lines, called from `/start`, `/checkpoint`, and the SessionStart hook
- `build_memory_compact(be, last_n)` — `task_logs` aggregation: phases + top words + top files

Likewise `scripts/model_routing.py` and `plugin_data.py` are pure modules imported by CLI/MCP handlers.

## Prompt Caching

TAUSIK relies on Anthropic's automatic prompt caching to keep agent runs cheap.
The framework itself does not call the API — Claude Code does — but the
*structure* of what TAUSIK feeds into each turn decides whether the API
caches a prefix or re-bills it. Cacheable surface, in priority order:

| Surface | Where it lives | Why it caches well |
|---|---|---|
| System prompt + tool schemas | Injected by Claude Code from `.claude/mcp/project/tools.py` and `tools_extra.py` | Identical across turns within a session — the longest stable prefix |
| `CLAUDE.md` | Project root | Read once per session and re-injected; stable unless `tausik_update_claudemd` rewrites the dynamic block |
| MCP tool descriptions | Same `tools.py` files | Editing them invalidates the cache — every wording change rewrites the prefix |
| Skills (`SKILL.md`) | `harness/skills/<name>/SKILL.md` | Loaded only when the skill activates |

**What invalidates the cache mid-session.** Editing any of the files above
between turns rewrites the prefix and forces the next turn to pay
`cache_creation_input_tokens` instead of `cache_read_input_tokens`. The
biggest offender is `tausik_update_claudemd` — running it mid-session
rewrites the dynamic-state block (session #, task counts, etc.) and the
entire `CLAUDE.md` prefix re-caches. Run it at session boundaries (`/start`,
`/checkpoint`, `/end`), not between regular tool calls.

**Verifying caching is actually active.** Anthropic returns
`cache_creation_input_tokens` (the prefix was just laid down) and
`cache_read_input_tokens` (a later turn hit the cache) in every response's
`usage` block. `scripts/validate_prompt_caching.py` parses a Claude Code
transcript JSONL and reports both totals plus a hit-rate:

```bash
python scripts/validate_prompt_caching.py --auto
# or
python scripts/validate_prompt_caching.py path/to/transcript.jsonl
```

Exit code `0` = caching active (`cache_read_input_tokens > 0`);
`1` = prefix is unstable (creation > 0 but reads = 0);
`2` = API never returned cache fields. See [troubleshooting.md](troubleshooting.md)
"Prompt caching not active" for common failure modes.

## Testing

```bash
pytest tests/ -v                    # all tests (3844)
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

When adding or restructuring tests (new module vs extending an existing file, scoped pytest mapping), follow **[Testing principles](testing-principles.md)**.
