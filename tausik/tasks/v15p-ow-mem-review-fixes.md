---
slug: v15p-ow-mem-review-fixes
title: "[defect] Review fixes: meta_delete for undelegate + build_memory_block hardening"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: v15-ow-delegate-cli
scope: "scripts/backend_crud.py (meta_delete), scripts/service_delegate.py, scripts/service_knowledge_aggregates.py, scripts/service_knowledge.py (memory_block passthrough param), scripts/gate_qg0_renar.py (docstring), tests/test_ow_delegate.py + tests/test_memory_context_surfacing.py"
scope_exclude: "no new feature; no schema migration (meta_delete is a query)"
relevant_files:
  - "scripts/backend_crud.py"
  - "scripts/service_delegate.py"
  - "scripts/service_knowledge_aggregates.py"
  - "scripts/service_knowledge.py"
  - "scripts/gate_qg0_renar.py"
  - "tests/test_ow_delegate.py"
  - "tests/test_memory_context_surfacing.py"
  - "docs/_generated/constants.json"
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T20:45:58Z"
---

## Goal

Apply adversarial-review (sonnet) findings on delegate-cli + context-memory surfacing: (delegate) add a real backend meta_delete so task_undelegate removes the row instead of leaving an empty tombstone, and stop printing 'parent session #None'; (memory_block) add a max_contexts param (was coupled to max_decisions), wrap build_memory_block in the same defensive try/except as build_compact_memory_tail, and use .get('id') consistently; (renar) de-confuse the _is_high_stakes 'fallback' docstring framing.

## Acceptance Criteria

AC1: backend gains meta_delete(key) (DELETE FROM meta WHERE key=?); task_undelegate uses it — no empty tombstone row left behind. AC2: build_memory_block takes max_contexts (default 5), not coupled to max_decisions; wrapped in try/except returning '' on backend error (parity with build_compact_memory_tail); uses .get('id'). AC3: the delegate idempotent message renders 'parent session #unknown' (not '#None') when no session. AC4: gate_qg0_renar docstring states tier OR complexity (either sufficient), not 'fallback'. AC5: tests cover meta_delete removal, max_contexts independence, build_memory_block error→'', and the #unknown formatting; ruff+mypy clean; filesize<400. Negative: a backend failure inside build_memory_block returns '' (no crash); undelegate on a non-delegated task stays a no-op.

## Plan

## Rollback

git revert; all changes are additive/defensive, no schema or behavior removal.

## Journal

- 2026-06-14T20:45:58Z [implementation] — AC1: ✓ backend meta_delete added; task_undelegate uses it — test_undelegate_removes_meta_row (meta_get None, no tombstone). AC2: ✓ build_memory_block has max_contexts (default 5) decoupled from max_decisions + try/except→'' parity + .get('id') — test_max_contexts_independent_of_max_decisions, test_memory_block_backend_error_returns_empty. AC3: ✓ idempotent message renders '#unknown' not '#None' — test_idempotent_message_no_session_shows_unknown. AC4: ✓ renar docstring states 'tier OR complexity (either sufficient)'. AC5: ✓ 28 tests green; ruff+mypy clean (209 files); files<400. Knowledge: memory #171. Root cause (category: regression): undelegate used empty-string tombstone + build_memory_block lacked the sibling's defensive guard. Prevention: real meta_delete + audit sibling aggregates for parity. Negative: build_memory_block backend error→'' (no crash); undelegate non-delegated = no-op.
