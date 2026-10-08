---
slug: r111-bounded-work-packet
title: "Build one bounded work packet for task context, search and source evidence"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: null
scope_exclude: "No database schema, hook enforcement, unrelated host profile, external tracker, release metadata or generated site changes. Source excerpts are limited to the active task scope and relevant files."
relevant_files:
  - "scripts/work_packet.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/skills/task/SKILL.md"
  - "tests/test_work_packet.py"
  - "changelog.d/bounded-work-packet-111.md"
  - "docs/ru/cli-tasks.md"
scope_paths:
  - "scripts/work_packet.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/skills/task/SKILL.md"
  - "tests/test_work_packet.py"
  - "changelog.d/bounded-work-packet-111.md"
  - "docs/ru/cli-tasks.md"
scope_tools: []
depends_on:
  - r111-round-topology
completed_at: "2026-10-01T20:54:28Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 1
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Replace repeated task-show, memory, search and file-read turnbacks with one bounded, source-addressed work packet assembled by the existing service layer.

## Acceptance Criteria

AC-1 One ProjectService implementation is exposed through thin CLI and MCP wrappers. AC-2 The packet has a configurable byte ceiling, source addresses and explicit overflow or omission metadata. AC-3 A frozen replay of a selected topology target contains the information required by the original sequence while removing at least two model return boundaries. AC-4 Negative: unreadable, out-of-scope or oversized sources are refused or named as omitted; no silent truncation and no bypass of task scope.

## Plan

[{"step": "Define the frozen packet contract from the topology evidence", "done": true}, {"step": "Implement one service composition over existing readers", "done": true}, {"step": "Expose thin CLI and MCP transports plus skill guidance", "done": true}, {"step": "Prove boundedness, scope refusal and replay equivalence", "done": true}]

## Rollback

Remove the work-packet endpoint and wrappers; existing individual task, memory, search and file-read operations remain authoritative.

## Journal

- 2026-10-01T20:35:20Z [planning] — IMPLEMENTATION INPUT: real topology target retrieval-to-retrieval occurred 116 times across 18 accepted windows and 1566 rounds. The packet must replace at least two model return boundaries, reuse existing task/search/memory readers, enforce an explicit byte ceiling, and name every omission.
- 2026-10-01T20:39:08Z [implementation] — Resumed checkpoint #279 at plan 0/4. Complex implementation delegated to Sol Medium; root checks acceptance inputs independently. Existing CLI bash wrapper fails on this Windows shell with /mnt/d translated path; fallback is python scripts/project.py. MCP session start lacks host-id, so use CLI host-id to avoid reusing older concurrent sessions.
- 2026-10-01T20:40:16Z [implementation] — Step 1 done: frozen packet v1 contract defines explicit query/source inputs; task context + FTS + memory + full source excerpts; packet byte ceiling; address fields; explicit omitted reasons; frozen four-return retrieval replay must preserve requested facts and remove three model-return boundaries.
- 2026-10-01T20:46:16Z [implementation] — Step 2 done: scripts/work_packet.py is the single transport-free composition over build_task_context_package, ProjectService.search, ProjectService.memory_search and a project-contained scope-checked UTF-8 source reader. Exact serialized bytes, fixed context allocation, full-unit admission and explicit omissions enforce the ceiling.
- 2026-10-01T20:46:25Z [implementation] — Step 3 done: thin CLI `task show --work-packet --query ... --source ...` and MCP `tausik_task_show(work_packet=true, query, sources, max_bytes)` call the same serializer. Skill and Russian CLI guidance document addresses, omissions, fixed context allocation and refusal semantics; no new MCP tool/count cascade.
- 2026-10-01T20:48:03Z [implementation] — Step 4 done: 27 targeted tests pass. Frozen offline replay executes the original task-context/search/memory/source sequence, compares goal, AC, search fact, memory fact and complete source content to one packet, and proves 4 returns -> 1 (3 boundaries removed) against the frozen retrieval→retrieval topology target. Negative tests prove resolved-path scope/exclude precedence, unreadable UTF-8, missing/outside, oversized and excessive-source refusals; exact UTF-8 byte accounting stays within ceiling.
- 2026-10-01T20:54:24Z [implementation] — AC verified: 1. PASS — tests/test_work_packet.py transport parity proves one canonical service-layer composer is exposed through thin CLI and MCP wrappers. 2. PASS — exact UTF-8 ceiling tests and live 14541/16384 packet prove configurable bounds, addresses, overflow and omissions. 3. PASS — frozen replay executes four original readers, preserves goal/AC/search/memory/full source content, and collapses 4 returns to 1 (3 boundaries); topology evidence confirms retrieval-to-retrieval target. 4. PASS — behavioral tests refuse resolved-path escape, scope_exclude, out-of-scope, missing, non-UTF8, oversized, duplicate and excessive sources with named reasons. Scoped verify #3310 passed: static gates green; pytest scoped 54/652 files; MCP surface ratchet green; bootstrap drift green.
- 2026-10-01T20:54:38Z [done] — AC-1: ✓ `tests/test_work_packet.py::test_cli_and_mcp_are_thin_transports_over_same_packet` and default-ceiling parity exercise one canonical `work_packet` composer through both wrappers. AC-2: ✓ exact UTF-8 `bytes <= max_bytes`, explicit address/overflow/omitted assertions, and live CLI packet 14541/16384. AC-3: ✓ frozen replay executes task context + search + memory + source reads, compares goal/AC/task hit/memory content/full source content, and proves 4 returns → 1 (3 boundaries removed) against round-topology retrieval→retrieval evidence. AC-4: ✓ parametrized and real-file tests name refusals for missing/outside, scope_exclude, non-UTF8, oversized, duplicate/excess sources and resolved symlink escape. Domain: a live project CLI invocation returned the actual active-task context, indexed task hit and complete scope-allowed scripts/work_packet.py content under the declared ceiling; scoped verify #3310 passed over 54/652 mapped test files with surface ratchet and bootstrap parity green.
