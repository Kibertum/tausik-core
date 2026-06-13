# TODO & Roadmap

This file tracks the project direction. The authoritative, fine-grained backlog
lives in the project database (`tausik roadmap` / `tausik task list`); this file
is the human-readable map of where TAUSIK is going and why.

> Released: **v1.5.0** (pre-2.0 hardening — signed verification receipts,
> SENAR enforcement core, fail-closed gates). See [CHANGELOG](CHANGELOG.md).

---

## 🎯 2.0 — Global MCP (the major rewrite)

**Goal:** make TAUSIK a *systemwide* tool, not a per-project git submodule.
Today every project vendors a `.claude/` copy and the MCP server is pinned to a
single project at spawn (`--project` + one `os.chdir`). 2.0 turns the engine
into a standalone, installed-once service that serves **many** projects from one
daemon. Background analysis: [`tausik_systemwide_analysis.md`](tausik_systemwide_analysis.md).
Architecture decision: **#94**.

The pivot is **spawn-time → request-time resolution**: the server must resolve
the project root (and its `.tausik/tausik.db`) *per request* via a connection
pool keyed by project root, instead of being bound to one project for its
lifetime.

| Task | Pri | What |
|---|---|---|
| `gmcp-spike-roots` | P0 | Spike: MCP roots-capability + Claude Code launch model |
| `gmcp-project-resolver` | P0 | `resolve_project()` — roots → pointer → cwd/env chain |
| `gmcp-server-multitenant` | P0 | Multi-tenant server: per-request resolve instead of `--project` |
| `gmcp-packaging` | P0 | Packaging: build-system + entry-points (`tausik` / `tausik-mcp`) |
| `gmcp-init-lite` | P1 | `tausik init`: only `.tausik/` + user-scope MCP registration |
| `gmcp-migrate-submodule` | P1 | Migrate existing projects from submodule → global |
| `gmcp-global-hooks` | P1 | Global hooks served from the installed library |
| `gmcp-version-skew` | P1 | Version-skew contract: one library, many project DBs |
| `gmcp-multi-ide` | P2 | Multi-IDE: Cursor/Qwen global registration (or an honest gap) |
| `gmcp-docs-global` | P2 | Docs EN+RU: install / upgrade / migrate, deprecate the submodule |

Supporting engine work (found during v1.5 hardening):

| Task | What |
|---|---|
| `v2-mcp-request-time-db-routing` | DB resolution spawn-time → request-time (connection pool per project root) |
| `v2-engine-standalone-package` | Engine as a pip-installable package; `.claude/` becomes an optional IDE adapter |
| `v2-stale-mcp-reaping` | Reap stale MCP servers (or single daemon) — kills the drift/hang class (#77/#79/#80) |

---

## 🛠 Post-1.5 — the 1.x track (before 2.0)

Deferred from v1.5 to keep the release a focused hardening cut (scope decision
#95). Nothing dropped — sequenced here.

**Snippets** (reusable-artifact detection & search)
- `v15-snippet-classifier` — heuristic `detect_artifact_kind()` + advisory wire
- `v15-snippet-table` — dedicated `snippets` table + migration
- `v15-snippet-ast-detect` — AST-based clone detection (`tausik snippet detect`)
- `v15-snippet-mcp-search` — `tausik_snippet_search` semantic search
- `v15-snippet-brain-integration` — `extract --scope brain` writes a snippet to Notion

**Orchestration**
- `v15-orchestrator-worker-pattern` — task-delegation primitive (orchestrator/worker)

**Model routing** (remaining, after the v1.5 fable-tier fix)
- `v15mr-phase-matrix` — phase × complexity matrix for model selection
- `v15mr-phase-surfaces` — phase hints in plan/explore/task starts
- `v15mr-subagent-model-hints` — model hints for subagents (research = haiku)
- `v15mr-routing-telemetry` — routing-adherence telemetry in metrics

**RENAR conformance** (`v16r-*` — reasoning trace + spec/conformance layer)
- `v16r-reasoning-steps-table` / `v16r-reason-skill` — reasoning_steps + `/reason`
- `v16r-model-pinning` — model-version pinning per task
- `v16r-task-replay` — reconstruct a task timeline
- `v16r-audit-hashchain` — hash-chain immutability for the event log
- `v16r-spec-types` — SPEC artifacts: 9 closed types (ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS)
- `v16r-adapt-lite` — forward interpretation + backward findings + dual signature
- `v16r-drift-detectors` — drift-1 (schema) + drift-7 (test↔requirement provenance)
- `v16r-conformance-yaml` — `RENAR-CONFORMANCE.yaml` self-assessment generator

**Shared Brain hardening** (`brainh-*`)
- `brainh-audit` — brain pain-point audit → improvement spec
- `brainh-reliability` — offline queue + local-first sync + health
- `brainh-semantic-search` — local embeddings
- `brainh-capture-ux` — auto-capture nudge on task done / session end
- `brainh-outline-spike` — spike: Outline as an alternative brain backend

---

## 📣 Release & adoption

- [ ] One-line install script (`curl ... | bash`) to cut onboarding friction
- [ ] Add a GIF/asciinema demo to the README (the agent hitting a BLOCKED gate, then the happy path)
- [ ] Verify GitHub repo + CI badges
- [ ] Publish to PyPI (ties into `gmcp-packaging`)
- [ ] Example project demonstrating the TAUSIK workflow
- [ ] Gather community feedback on the skill system

---

## 🔭 Loose threads

- [ ] `notify_on_done` hook (Discord/Slack/Telegram on `task_done`). Implementation existed but was removed in 1.3.6 as an orphan — restore from git history and register a PostToolUse in `bootstrap_generate.py` + optional `.tausik/config.json` (channel + webhook).
- [ ] Evaluate **Outline** as an alternative self-hosted backend for the Shared Brain (API + FTS out of the box) — revisit vs Notion after MVP (tracked as `brainh-outline-spike`).
