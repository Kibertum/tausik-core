---
slug: second-full-run-red-after-rename-and-format
title: "Second full run of session #269: two reds left by the rag rename and a formatted legacy test"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_mcp_answers_prompts_list.py"
  - "tausik/gates.json"
  - "tests/test_gate_ruff_format.py"
scope_paths:
  - "tests/test_mcp_answers_prompts_list.py"
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:55:35Z"
resolution: null
resolution_reason: null
---

## Goal

The two tests red in the second full run are fixed at their cause: a server discovery glob the rag rename missed, and a legacy-list entry for a test file that got formatted.

## Acceptance Criteria

1. tests/test_mcp_answers_prompts_list.py discovers both harness MCP servers again — the glob names the entry points (server.py and rag_server.py), not one file name. 2. tests/test_knowledge_origin.py leaves ruff_format.legacy_unformatted in tausik/gates.json because it is formatted now (the list only shrinks). 3. NEGATIVE: the discovery guard still demands at least two servers, so a glob that matches one would stay red.

## Plan

## Rollback

git revert

## Journal

- 2026-09-23T23:55:00Z [implementation] — AC-1: ✓ tests/test_mcp_answers_prompts_list.py::test_servers_were_discovered — the glob matches '*server.py', discovering harness/claude/mcp/project/server.py and harness/claude/mcp/codebase-rag/rag_server.py.
- 2026-09-23T23:55:00Z [implementation] — AC-2: ✓ tests/test_gate_ruff_format.py::test_the_legacy_list_only_shrinks — tests/test_knowledge_origin.py removed from ruff_format.legacy_unformatted.
- 2026-09-23T23:55:00Z [implementation] — Root cause: (a) the rename task grepped for 'codebase-rag/server' and never saw a glob of '*/mcp/*/server.py' that names neither the package nor the path; (b) ruff format over tests/test_knowledge_origin.py in the absoluteness task made a frozen legacy entry stale. Both were caught only by the full run — the scoped verifies of those tasks did not select these tests.
- 2026-09-23T23:55:01Z [implementation] — AC-3: ✓ tests/test_mcp_answers_prompts_list.py::test_servers_were_discovered — negative, its >=2 assertion is unchanged, so a glob matching one server stays red (it was exactly that red before this fix).
