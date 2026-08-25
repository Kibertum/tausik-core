---
slug: mcp-scope-empty-list-legacy-freedom
title: "mcp_tool_scope: scope_tools='[]' читается как legacy-freedom вместо core-only (парсит truthiness, не raw)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: mcp-scope-tools-exposure
scope: "scripts/mcp_tool_scope.py (_active_declared_tools raw-value check); tests/test_mcp_tool_scope.py (fix the dishonest test + add solo-[] core-only assertion). Also refine SAFE_CORE naming/comment honesty (LOW review finding)."
scope_exclude: null
relevant_files:
  - "scripts/mcp_tool_scope.py"
  - "tests/test_mcp_tool_scope.py"
scope_paths:
  - "scripts/mcp_tool_scope.py"
  - "tests/test_mcp_tool_scope.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-27T13:42:38Z"
---

## Goal

_active_declared_tools проверяет `if tools:` на РАСПАРСЕННОМ списке, а parse_task_acl схлопывает и NULL, и '[]' в один Python []. Поэтому одиночная активная задача с scope_tools='[]' (явное «никаких доп. тулов») трактуется как legacy-freedom (None) → экспонируются ВСЕ тулы, вместо ограничения до safe-core. Это противоречит докстрингу mcp_tool_scope (строки 92-96) и ломает симметрию со scope_write_gate, который читает RAW-значение (raw is not None), а не truthiness распарсенного. Фикс: различать '[]' (declared → restrict to core) и NULL (undeclared → legacy freedom) по сырому значению DB, зеркаля scope_write_gate.has_declared_scope.

## Acceptance Criteria

1. A SOLO active task with scope_tools='[]' (explicit empty, declared) restricts the exposed surface to the always-safe-core ONLY — NOT legacy freedom — mirroring scope_write_gate's raw-value semantics ('[]' = explicit declaration). 2. NEGATIVE/boundary: a solo active task with scope_tools NULL (never declared) still yields ALL tools (legacy freedom) — the '[]' vs NULL distinction is honored by reading the raw DB value, not the parsed list truthiness. 3. The misleading test test_empty_declared_list_restricts_to_core_only in tests/test_mcp_tool_scope.py is corrected to actually assert the core-only behavior for a solo [] task (fails against the old code, passes after the fix) — no dangling 'Assert that first' with only the opposite case checked. 4. Full scoped verify green; ruff + mypy clean.

## Plan

## Rollback

git revert — localized change to _active_declared_tools (raw-value check) + one test rewrite; no schema/data change, no runtime surface beyond the already-fail-open filter.

## Journal

- 2026-07-27T13:42:26Z [implementation] — Root cause: scope_acl._parse_list (the lenient reader) intentionally collapses both scope_tools=NULL and scope_tools='[]' to the same Python []. _active_declared_tools inferred "declared" from the PARSED list's truthiness (`if tools:`), which cannot distinguish "never declared" (NULL → legacy freedom) from "explicitly declared empty" ('[]' → restrict to core). The authoritative signal is the RAW DB value (raw is not None), which scope_write_gate.has_declared_scope already uses correctly — that existing pattern was simply not reused in the new module. Fix: read task['scope_tools'] raw; None/'' → skip (undeclared), anything else → declared (parse for the tool names). Negative: solo active task scope_tools='[]' now restricts exposure to the safe-core (test_solo_empty_declared_list_restricts_to_core_only); solo NULL still yields all tools (test_solo_null_scope_is_legacy_freedom). Class of defect: trusting a lossy lenient-parser output where a raw-value distinction was semantically required.
- 2026-07-27T13:42:36Z [implementation] — AC verified: 1. ✓ tests/test_mcp_tool_scope.py::TestExposeScoped::test_solo_empty_declared_list_restricts_to_core_only — solo scope_tools='[]' → out == {tausik_status} (safe-core only), epic_add hidden. Behavioral repro: _active_declared_tools([]-task)=set(). 2. ✓ NEGATIVE: test_solo_null_scope_is_legacy_freedom — solo scope_tools NULL → all tools. Repro: _active_declared_tools(NULL-task)=None. '[]' vs NULL read from raw DB value, not parsed truthiness. 3. ✓ The misleading test_empty_declared_list_restricts_to_core_only (asserted the opposite case with a dangling 'Assert that first') is replaced by the two correct tests above — the first fails against the old code, passes after the fix. 4. ✓ verify --task standard pytest PASS (3 mapped files, 17 tests in test_mcp_tool_scope). ruff + mypy clean on scripts/mcp_tool_scope.py. Root cause logged (Rule 7). LOW review finding also addressed: SAFE_CORE comment made honest re mutating task_ members (write-gate is their barrier).
- 2026-07-27T13:42:47Z [done] — Root cause (logic-error): reader inferred "ACL declared?" from the lenient parser's output (parse_task_acl collapses NULL and '[]' to []), losing the NULL-vs-empty distinction; '[]' leaked as legacy freedom. Prevention: for the declared-vs-undeclared decision read the RAW DB column (raw is not None), never the parsed list — reuse scope_write_gate.has_declared_scope's pattern rather than re-deriving.
