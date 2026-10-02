---
slug: r111-prefix-dedup-lazy-schema
title: "Deduplicate project-controlled repeated prompt and lazy-load schemas"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 80
defect_of: null
scope: "Measure and reduce the project-controlled repeated prefix by enabling the existing compact MCP tool-list tier, preserving canonical instruction reachability, regenerating supported host profiles, and documenting same-surface before/after evidence."
scope_exclude: "No commit, push, release, GitLab #10, Kiberza hooks, paid or synthetic model benchmarks, new schema mechanism, or changes to SENAR enforcement semantics."
relevant_files:
  - "bootstrap/bootstrap_config.py"
  - "scripts/mcp_tool_tiers.py"
  - "tests/test_mcp_tool_tiers.py"
  - "tests/test_mcp_surface_ratchet.py"
  - "docs/en/context-economy.md"
  - "docs/ru/context-economy.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "changelog.d/prefix-dedup-lazy-schema-111.md"
scope_paths:
  - ".tausik/config.json"
  - "scripts/mcp_tool_tiers.py"
  - "bootstrap/"
  - "harness/"
  - "tests/test_mcp_tool_tiers.py"
  - "tests/test_mcp_surface_ratchet.py"
  - "docs/en/context-economy.md"
  - "docs/ru/context-economy.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "changelog.d/prefix-dedup-lazy-schema-111.md"
  - AGENTS.md
  - CLAUDE.md
  - ".codex/"
  - ".claude/"
  - ".cursor/"
  - ".kilocode/"
  - ".opencode/"
  - ".qwen/"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
scope_tools: []
depends_on:
  - r111-round-topology
completed_at: "2026-10-01T21:45:13Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Reduce project-controlled content repeated on every host turn by removing duplicated instructions and advertising only the minimum eager tool schema while preserving rule and tool reachability.

## Acceptance Criteria

AC-1 A frozen before and after inventory attributes bytes or tokens to AGENTS, skills, MCP descriptions and tool schemas without double counting. AC-2 Project-controlled repeated prefix falls by at least 30 percent on the same host surface. AC-3 Every removed instruction has one canonical reachable source and every deferred tool schema remains retrievable by name. AC-4 Negative: core task, verify, memory and recovery operations remain eagerly discoverable; no SENAR rule or enforcement statement disappears.

## Plan

[{"step": "Freeze and attribute the repeated project-controlled prompt surface", "done": true}, {"step": "Remove duplicated instruction text and defer non-core schemas", "done": true}, {"step": "Regenerate every supported host profile", "done": true}, {"step": "Measure the same surface and run reachability and parity gates", "done": true}]

## Rollback

Remove the project mcp.compact_tool_list override and revert only this task's profile/template/docs/test changes; the existing feature remains default-off.

## Journal

- 2026-10-01T21:33:26Z [implementation] — Step 1 frozen before edits on a fresh stdio MCP process with project config absent: 147 tools; minified serialized tools/list 54,566 B = names 3,974 + descriptions 17,722 + schemas 32,134 + JSON structure 736 (exact non-overlapping partition). Codex project-controlled eager inventory adds AGENTS.md 7,518 B and canonical 15-skill name/description catalog 1,249 B, for 63,333 B total without double counting. Skill bodies are deferred/on-demand and reported separately: 89,315 B, excluded from eager total. Same-host after measurement will use the identical probe and fresh process; stale running MCP is excluded.
- 2026-10-01T21:36:33Z [implementation] — Step 2 done: enabled existing root mcp.compact_tool_list flag; no new mechanism. Fresh tools/list remains 147 names, non-core full definitions remain retrievable through tausik_tool_schema, and the config-root boundary has a behavior test (26 passed).
- 2026-10-01T21:36:55Z [implementation] — Step 3 done: bootstrap --ide all redeployed Claude, Cursor, Qwen, Kilo/GLM, OpenCode and Codex profiles from the shared source; local configs were merged by the normal generator and the root mcp override remains present.
- 2026-10-01T21:45:03Z [implementation] — Step 4 done: final fresh-process eager inventory is 42,519 B versus frozen 63,333 B (-32.9%); 147 names remain, core quick/start/step/done/verify/memory/recovery schemas are eager, deferred schemas resolve by exact name, all supported profiles have zero bootstrap drift, and scoped verify #3323 passed.
- 2026-10-01T21:45:04Z [implementation] — Domain: MCP advertised tool surface, generated project configuration, and cross-host context economy. Root cause: the measured compact tier and exact-name schema recovery already existed, but generated project config did not enable it and the eager core omitted current task_quick/task_step entrypoints. AC-1 ✓ Frozen same-host fresh stdio inventory documents an exact non-overlapping byte partition in docs/en/context-economy.md and docs/ru/context-economy.md; raw-source size and stale MCP excluded; tests/test_mcp_surface_ratchet.py::TestTheSurfaceDoesNotGrowUnwatched::test_surface_is_within_the_baseline. AC-2 ✓ Eager project-controlled total 63,333 B -> 42,519 B (-32.9%) on the same 147-tool surface; tests/test_mcp_tool_tiers.py::TestЭкономияИзмеренаЧислом::test_экономия_не_меньше_трети. AC-3 ✓ Every deferred definition is canonically recoverable by exact name and bootstrap preserves explicit opt-out; tests/test_mcp_tool_tiers.py::TestВыгруженноеДостижимо::test_схема_по_точному_имени; tests/test_mcp_tool_tiers.py::TestПоУмолчаниюВыключено::test_bootstrap_enables_compaction_but_preserves_explicit_opt_out[False]. AC-4 ✓ Core workflow remains fully eager, including new task_quick/task_step entries; no AGENTS/SENAR instruction changed (7,518 B before/after), runtime fails open without valid config; tests/test_mcp_tool_tiers.py::TestЯдроСодержитНужноеНаПервомХоду::test_остаётся_в_ядре[tausik_task_step]; tests/test_mcp_tool_tiers.py::TestПоУмолчаниюВыключено::test_ошибка_чтения_конфига_читается_как_выключено. Verification: run #3323 PASS; targeted 30 + 63 + 3 slow tests green; dedupe audit 0 copies; bootstrap --ide all --check zero drift.
- 2026-10-01T21:46:53Z [done] — Natural Codex observation after closure: 46 attributed response rounds; Sol Medium Standard single identity; 5084849 total tokens incl4933760 cached input; one task-start attempt. Three complete natural accepted windows after bounded packet are99,50,46 rounds (median50), exceeding target40. Incomplete bounded-packet4-round window excluded. Source: incremental usage_codex_report accepted_task_cost.
