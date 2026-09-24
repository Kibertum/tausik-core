---
slug: rag-first-by-mechanism-not-text
title: "RAG as the code base: a PreToolUse mechanism answers Grep on unfamiliar code with search_code results"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: complex
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/rag_grep_context.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_rag_route_by_mechanism.py"
  - "docs/_generated/constants.json"
scope_paths:
  - "scripts/hooks/rag_grep_context.py"
  - "bootstrap/bootstrap_hooks.py"
  - "harness/skills/**"
  - "bootstrap/bootstrap_templates.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T07:13:32Z"
---

## Goal

RAG becomes the default route to code by mechanism: on Grep/Read of unfamiliar code a hook injects search_code results, so the index is used without the agent remembering to.

## Acceptance Criteria

1. A PostToolUse hook on Grep (registered in build_hooks_dict, so every host gets it) queries the project RAG index (.tausik/rag/rag.db, read-only) with the identifiers of the Grep pattern and injects the top chunks (path:lines + a few lines each, capped) as additionalContext. PostToolUse, not PreToolUse: additionalContext after the tool is the channel every host supports, and Grep still runs. 2. Skills and the host template name RAG again as the route to code, as an explanation of this mechanism; the inventory test is updated to the new decision #391. 3. NEGATIVE: an absent, empty or locked index, a non-Grep tool, or a pattern with no identifier adds nothing and exits 0. 4. NEGATIVE: effectiveness — search_code-derived context reaching the agent — is shown on a live Grep in this repository before closing; the paired replay stays a follow-up, not a claim.

## Plan

## Rollback

git revert; the hook leaves the shared declaration

## Journal

- 2026-09-24T07:11:42Z [implementation] — AC-1: ✓ tests/test_rag_route_by_mechanism.py::test_a_grep_brings_the_index_hits and tests/test_rag_route_by_mechanism.py::test_the_hook_is_registered_for_grep_on_every_host — scripts/hooks/rag_grep_context.py (PostToolUse, read-only sqlite mode=ro on .tausik/rag/rag.db, top 3 chunks, 1500-char cap) registered in build_hooks_dict next to the truncation nudge, so claude/qwen/codex get it.
- 2026-09-24T07:11:42Z [implementation] — AC-2: ✓ tests/test_rag_route_by_mechanism.py::test_the_inventory_of_mentions_is_frozen — skills debug/start/task/explore and bootstrap TOOL_ROUTING name RAG as the route to code again; the old test_rag_first_nudges_removed.py (decision #390(1)) is replaced by this file (decision #391).
- 2026-09-24T07:11:43Z [implementation] — AC-3: ✓ tests/test_rag_route_by_mechanism.py::test_nothing_is_added_when_there_is_nothing_to_add and tests/test_rag_route_by_mechanism.py::test_no_index_adds_nothing — negative: non-Grep, no identifier, no hit, no index -> exit 0, empty stdout; mutation (hit rows ignored) -> 1 failed, 9 passed; restored.
- 2026-09-24T07:11:43Z [implementation] — AC-4: ✓ measurement — live on this repository: Grep pattern 'def changed_files_since' -> '[TAUSIK RAG] Index hits for ... changed_files_since' with tests/test_service_verification.py:809-861 among the chunks. Paired replay remains a follow-up, no effectiveness claim beyond 'the context reaches the agent'.
- 2026-09-24T07:11:44Z [implementation] — Side effects handled: hooks_count 22 -> 23 regenerated in docs/_generated/constants.json; README/README.ru/docs hooks.md counts updated; hooks.md row added. 1093 hook/bootstrap tests green.
