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
| `knowledge_db.py` + `knowledge_write.py` + `knowledge_read.py` | The shared local store `~/.tausik-knowledge` (`--global` on `decide` / `memory add`; folded into `memory search`) |
| `publication_boundary.py` + `knowledge_export.py` | The one place shared-store content leaves the machine (`knowledge export --redacted`) |
| `cq_client.py` | Cross-project queue client |
| `doc_extract.py` | markitdown integration |
| `docs_lint.py` | Warning-only stale-version linter |
| `plan_parser.py` | Markdown plan parser for `/run` |
| `model_routing.py` | Model selection helper |
| `ide_utils.py` | IDE detection, paths, registry |
| `tausik_utils.py` + `tausik_version.py` + `project_types.py` | Helpers, version, types |
| `gen_doc_constants.py` | Doc-drift entry point: `--check`, `--write`, regenerate `constants.json` |
| `doc_drift_common.py` | Shared regex tables, scan targets, text helpers |
| `doc_drift_scanners.py` | The six drift scans (versions, MCP counts, closed lists, test and code counts) |
| `doc_drift_tables.py` | Numeric cells of markdown table columns, with their subject registry |
| `doc_drift_fixes.py` | The auto-fixer `--write` runs |
| `code_counts.py` | Counts repo state: hooks, stacks, roles, review agents, skills |
| `mcp_tool_counts.py` | Counts the MCP surface each server advertises |
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
| `analyzer.py` | ~260 | Extension-skill detection and tree walking |

### MCP Server

| File | Purpose |
|------|---------|
| `harness/claude/mcp/project/server.py` | JSON-RPC stdio server |
| `harness/claude/mcp/project/tools.py` | core tool definitions |
| `harness/claude/mcp/project/tools_extra.py` | extended tool definitions (skills, gates, doctor, verify, roles, stacks) |
| `harness/claude/mcp/project/handlers.py` | Dispatch only: tool-call counter, `handle_tool`, merge of the per-domain tables |
| `harness/claude/mcp/project/handlers_<domain>.py` | Handlers by domain: `task`, `session`, `status`, `knowledge`, `hierarchy`, `stack`, `role`, `verification`, `cq`, `skill`, `spec`, `adapt`. Each module exports `<DOMAIN>_HANDLERS`; `handlers.py` merges them into `_DISPATCH` |
| `harness/claude/mcp/project/handlers_render.py` | Shared list rendering (`render_list`) — an empty result must read as "nothing here", not as an empty string |

Total MCP surface: **146 project tools** (optional
`codebase-rag` adds 7 more; not part of the main count).

**THAT SURFACE IS PAID FOR ON EVERY TURN, AND THE PRICE DIFFERS BY HOST.** The
MCP protocol sends every tool's name AND schema each turn unless the client
defers schemas. Measured in session #229: the project server's serialized
definitions are 56,108 bytes (~14,000 tokens); the names alone are 3,201 bytes
(~800 tokens) — a 17.5x difference. Claude Code defers and pays the names, which
was OBSERVED; a host without deferral pays the whole thing, which follows from
the protocol and was not observed here.

The figures above are for reading, not the source of truth: that is the
`mcp_surface` ratchet in `tausik/gates.json`, which
`tests/test_mcp_surface_ratchet.py` re-measures on every run and turns red on
growth. It is done that way because the previous version of this number rotted
in exactly this spot — the task filed 117 tools and 44,501 bytes in session #178,
and by #229 it was 145 and 56,108: 24% and 26% of growth nobody noticed while the
number lived in prose.

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

**How that was measured, and how to measure it again.** The headers are not
"obviously helpful" — their gain is counted by a reproducible instrument,
`scripts/rag_retrieval_bench.py` (`python scripts/rag_retrieval_bench.py
[--limit N] [--json]`). It derives its queries MECHANICALLY from the corpus and
samples them deterministically, so the set cannot be tuned toward a flattering
result and two runs over the same tree ask the same questions. It measures
recall@K against the SPECIFIC CHUNK and keeps two query sets at once: `context`,
the case the header exists for, and `control`, queries built only from words
already inside the chunk, where the header must not help and above all must not
hurt. At n=115: recall@3 went 0.4870 → 0.8348 on `context` and 0.5739 → 0.6435
on `control`, with no regression at any K.

### Cross-IDE Support

Skills, roles, stacks -- shared across IDEs. So are the MCP servers: `harness/claude/mcp/`
is the single canonical tree, and `copy_mcp` hands it to every IDE that has none of its
own (all of them, today). A per-IDE copy would be a mirror waiting to drift — one used to
exist under `harness/cursor/` and was deleted in v1.7.0.
```
harness/
+-- skills/           # 13 core auto-deployed + 20 in skills-official/ (opt-in via --include-official)
+-- roles/            # 7 roles (architect, developer, devops, qa, researcher, tech-writer, ui-ux)
+-- stacks/           # Stack guides
+-- overrides/        # IDE-specific overrides (claude/, cursor/, qwen/)
+-- claude/mcp/       # MCP servers (project, codebase-rag) — canonical for ALL IDEs
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
`renar_drift_schema`, `renar_drift_provenance`, `cross_model_parity`.

`cross_model_parity` asks one question: did a capability go host-only without
anyone saying so. It RUNS the real mechanism generators into a clean tree and
compares hosts that share an extension point — Claude's hooks against Qwen's,
plugins against plugins. There is no comparison ACROSS kinds: asking whether
Claude is "missing" OpenCode's plugin is a question with no meaning. The gate does
NOT demand sameness: Cursor has no extension point at all, so there is nothing for
it to be equal to. What it demands is that a difference be NAMED, with a reason —
and a declaration that no longer matches any live difference is refused as loudly
as an undeclared difference (decision #335). It fires only on host-layer edits
(`bootstrap/`, `scripts/hooks/`, `harness/opencode/`): a gate that asks every task
about cross-model parity is a tax, and a tax gets switched off.

`bootstrap_drift` checks all three links of the chain "edit → deploy → takes
effect": `scripts/` against the deployed profile, `harness/` against its
fan-out, and the deployed profile against **the process that runs from it**
(`running_source_drift`: a content snapshot at process start, compared at
task-done). A long-lived MCP server whose profile was rewritten underneath it
executes the old copy; the gate refuses the close and names the fix — restart
the server, or close via the CLI, which is a fresh process.

**A gate is verified by mutation, not by passing.** A green run proves only
that the gate did not object — not that it would object to anything. The rule
is held by `tests/test_gates_catch_their_violation.py`: every gate in
`gate_registry.GATE_REGISTRY` is in exactly one of two tables. COVERED — the
gate is driven through the registry's own `impl_for` on BOTH ends: a real
violation built under `tmp_path` must come back failed, a clean input built the
same way must come back passed (one end alone is empty: a gate that is red on
every input passes a red-only check as well as a correct one). EXCUSED — a gate
that cannot be driven from a synthetic tree (service-bound, an external tool's
verdict, warn severity), with a reason and the names of a red and a green test
in the module that does drive it; the names are checked against that module's
AST. The list is closed: a new gate without a row reddens the lane. A mutation
cannot stay in the tree by construction — everything is built under
`tmp_path`, and a write outside it during the table run is caught by
intercepting `open`, `sqlite3.connect` and `subprocess` (the three channels
the builders use) — not by a `git status` snapshot, which under xdist loses
the race to a neighbouring worker.

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
| Handoff contract | `tausik task handoff <slug>` — deterministic JSON {slug, goal, acceptance_criteria, scope, scope_exclude, model, skills}; the trimmed `WORKER_SKILLS` profile (no plan/explore). The orchestrator passes it to the Agent tool; the worker echoes it back (round-trip identity). |
| In-session recognition | `task start` on a delegated task surfaces **worker mode** (operating contract) and suppresses the orchestrator-only model-recommendation banner. |
| Scope hard-gate | the worker is scope-bounded — `scope_write_gate` blocks edits outside `scope_paths`, and a delegated task with **no** scope is blocked until it declares one (no legacy fail-open for workers). |
| Summary-back | `tausik task summary-back <slug> "<summary>" [--gates …]` — the worker returns a structured result (stored in `meta`, surfaced in `task show`) so the coordinator picks it up **without** the worker transcript. |

Delegation state is CLI-first (no MCP surface, to avoid doc-count drift) and
lives entirely in the `meta` table (`delegation:<slug>`, `worker_summary:<slug>`).

## Hooks (anti-drift, see [hooks.md](hooks.md))

All hook files under `scripts/hooks/` are registered via `bootstrap/bootstrap_generate.py` (Claude Code) and `bootstrap/bootstrap_qwen.py` (Qwen Code). Hook scripts are non-blocking (exit 0); errors go to stderr. Shared helpers live in `scripts/hooks/_common.py`.


## Memory Aggregates

`service_knowledge_aggregates.py` holds pure functions for memory re-injection:

- `build_memory_block(be, ...)` — compact markdown (decisions + conventions + dead ends), ≤50 lines, called from `/start`, `/checkpoint`, and the SessionStart hook
- `build_compact_memory_tail(be)` — the one-line-per-entry recap embedded in the CLAUDE.md dynamic block
- `build_memory_compact(be, last_n)` — `task_logs` aggregation: phases + top words + top files

Both recaps read the memory graph through `memory_supersedes.live_head`: an
entry a LIVE `supersedes` edge has retired is not printed, its line goes to the
next live entry, and the surviving entry says `(supersedes #N)` on the line it
occupies anyway. Only that relation hides anything, and only when the
superseding entry is itself unarchived — otherwise the older entry is the best
knowledge left. An unreadable graph retires nothing, so the recap degrades to
what it printed before the filter existed.

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
