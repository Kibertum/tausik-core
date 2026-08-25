---
slug: v14b-mcp-stale-module-detector
title: "Stale MCP module detector — root fix for task_done_v2 hang"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 80
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T21:20:33Z"
---

## Goal

Detect stale MCP project servers (in-memory modules older than current source mtime) and surface a prominent warning at session start so the user restarts the IDE before hitting silent hangs in `tausik_task_done_v2`/`tausik_verify`. Companion to gotchas #77, #79, #80.

## Acceptance Criteria

1. New MCP tool `tausik_self_check` returns JSON with: server name, pid, startup_time_iso, watched_modules dict (path→snapshot_mtime), drift_detected bool, stale_modules list, sibling_mcp_count int.
2. MCP `agents/claude/mcp/project/server.py` (or a new `agents/claude/mcp/project/self_check.py` module) captures `_STARTUP_TIME` (UTC ISO) and `_MODULE_MTIMES_AT_STARTUP` for a curated watch-list at module-import time. Watch-list: scripts/service_verification.py, scripts/gate_runner.py, scripts/service_gates.py, scripts/service_task.py, scripts/verify_cache.py, scripts/security_pattern.py, scripts/gate_command_runner.py, scripts/project_service.py, agents/claude/mcp/project/handlers.py, agents/claude/mcp/project/server.py.
3. `drift_detected=True` when any watched module's current `os.path.getmtime` is newer than the snapshot.
4. `sibling_mcp_count` enumerates other python processes whose cmdline contains `mcp/project/server.py --project <same-project>` and excludes self pid. Best-effort, no crash if process introspection unavailable. On Windows uses `wmic`; on POSIX uses `/proc` or `ps`. Failure → returns -1 with a warning string in result.
5. Tool registered in `tools_extra.py` with description that mentions the stale-module hang gotchas (#77, #79, #80) so the agent has context when calling it.
6. `/start` skill (Phase 1) MUST call `tausik_self_check` after `tausik_session_start` and before Phase 1.5 brain primer. If `drift_detected` is true OR `sibling_mcp_count > 0` → render a top-of-dashboard `⚠ MCP Health` block listing stale modules and sibling PIDs, with `Recommendation: restart IDE before continuing` text. If clean → render nothing or a single OK line.
7. Tests in `tests/test_mcp_self_check.py` (NEW, ≥4 cases): snapshot capture happens at import; drift detected when file mtime advances after snapshot; no drift when unchanged; sibling count returns int (≥-1) without crashing on platforms where introspection fails. Plus `tests/test_skill_cli_help.py` (or equivalent) updated with the new tool in tool count if applicable.
8. Docs: `docs/en/mcp.md` + `docs/ru/mcp.md` — new tool entry with description + when-to-call. `docs/en/troubleshooting.md` (NEW or existing) + `docs/ru/troubleshooting.md` — section "Stale MCP modules" referencing gotchas #77/#79/#80 and remediation (restart IDE; explicit `verify_pipeline_timeout_seconds` in config).
9. `agents/skills/start/SKILL.md` updated: Phase 1 adds `tausik_self_check` to the parallel batch; Phase 3 adds an MCP-health line item.
10. CHANGELOG.md + CHANGELOG.ru.md: bilingual `### Added` entry under `[Unreleased] — v1.4.0 polish (Phase B)` mentioning the detector and the rendering in /start.
11. Pytest fast lane + ruff green.
12. `tausik verify --task v14b-mcp-stale-module-detector` GREEN; close via `task done --ac-verified`.

## Plan

[{"step": "Read agents/claude/mcp/project/server.py + handlers.py + tools_extra.py to map current shape", "done": true}, {"step": "NEW agents/claude/mcp/project/self_check.py: snapshot module mtimes at import + sibling enumeration helper (cross-platform)", "done": true}, {"step": "agents/claude/mcp/project/server.py: import self_check at startup so snapshot fires", "done": true}, {"step": "tools_extra.py: register tausik_self_check tool definition", "done": true}, {"step": "handlers.py: add _handle_self_check that calls self_check.collect()", "done": true}, {"step": "scripts/project_service.py or service_diagnostics.py: thin service method (optional \u2014 may live in MCP-only module)", "done": true}, {"step": "tests/test_mcp_self_check.py NEW: \u22654 cases (snapshot, drift, no-drift, sibling count graceful)", "done": true}, {"step": "agents/skills/start/SKILL.md: Phase 1 adds tausik_self_check; Phase 3 renders MCP Health block", "done": true}, {"step": "docs/en/mcp.md + docs/ru/mcp.md: tool entry", "done": true}, {"step": "docs/en/troubleshooting.md + docs/ru/troubleshooting.md: Stale MCP modules section (NEW or extend)", "done": true}, {"step": "CHANGELOG.md + CHANGELOG.ru.md bilingual entry", "done": true}, {"step": "ruff + pytest fast lane green", "done": true}, {"step": "tausik verify --task + task done --ac-verified", "done": true}]

## Rollback

## Journal

- 2026-05-03T21:20:10Z [implementation] — Implementation complete. NEW agents/claude/mcp/project/self_check.py (mirrored to cursor/) — eager-imports 11 watched modules, snapshots mtimes at MCP startup, exposes collect() with drift_detected + sibling_mcp_count. server.py imports self_check pre-loop. tools_extra.py registers tausik_self_check. handlers.py adds _handle_self_check. tests/test_mcp_self_check.py 6/6 PASS. /start skill Phase 1 + Phase 3 wired. docs/{en,ru}/mcp.md + troubleshooting.md updated. Tool count bumped 92→93 project, 99→100 main, 106→107 with RAG; gen_doc_constants regenerated; AGENTS/README/architecture/agent-contract synced. CHANGELOG bilingual entry. Full pytest 2606 PASS, 7 skip, ruff clean.
- 2026-05-03T21:20:29Z [implementation] — AC verified: 1. ✓ tausik_self_check returns server, pid, startup_time_iso, watched_modules dict, drift_detected, stale_modules, sibling_mcp_count. 2. ✓ self_check.py captures _STARTUP_TIME_ISO + _MODULE_MTIMES_AT_STARTUP at import; watch-list covers service_verification, verify_cache, security_pattern, gate_runner, gate_command_runner, service_gates, service_task, project_service, project_backend, handlers, handlers_skill (11). 3. ✓ drift_detected=True when current mtime > snapshot+0.001s (test_drift_detected_when_mtime_advances). 4. ✓ sibling enumeration cross-platform (wmic on Windows, /proc on POSIX, ps fallback); on failure returns -1 with error string (test_sibling_count_is_safe_int). 5. ✓ Tool registered in tools_extra.py with description naming gotchas #77/#79/#80 + remediation. 6. ✓ /start SKILL.md Phase 1 batch + Phase 3 ⚠ MCP Health block. 7. ✓ tests/test_mcp_self_check.py NEW: 6 cases (snapshot populated; no drift unchanged; drift on mtime advance ≥30s; missing files don't crash; sibling int (≥-1) safe; handler returns valid JSON). 8. ✓ docs/{en,ru}/mcp.md tool entry under Status, Health, Metrics; docs/{en,ru}/troubleshooting.md NEW 'Stale MCP modules (silent hangs)' section. 9. ✓ agents/skills/start/SKILL.md Phase 1 includes tausik_self_check; Phase 3 renumbered to add MCP Health item 2. 10. ✓ CHANGELOG.md + CHANGELOG.ru.md bilingual ### Added entry under [Unreleased] — v1.4.0 polish (Phase B). 11. ✓ Full pytest fast lane: 2606 passed, 7 skipped, 118 deselected, 74.51s. ruff: All checks passed. 12. ✓ tausik verify --task v14b-mcp-stale-module-detector → Recorded verification_run (exit=0). Tool counts updated 92→93/99→100/106→107 across AGENTS/README+ru/docs/agent-contract; gen_doc_constants regenerated; cursor/mcp/project mirrored for parity.
