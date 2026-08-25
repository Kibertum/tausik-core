---
slug: fix-memory-block-case-fold
title: "memory_pretool_block: case-insensitive segment match always"
status: done
epic: v131-blind-review-fixes
story: security-high
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 8
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/memory_pretool_block.py"
  - "tests/test_v131_blind_review.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:03:28Z"
---

## Goal

Lowercase memory segment compare unconditionally (was win32-only). On Linux/macOS path .../MEMORY/x.md or .../Memory/x.md bypasses the block. Closes HIGH (Sec).

## Acceptance Criteria

1. memory_pretool_block: lowercase segment compare unconditionally; 2. Test asserts MEMORY/, Memory/, memory/ all blocked on Linux; 3. Negative: writing to ~/.claude/projects/foo/MEMORY/x.md no longer slips through on Linux.

## Plan

## Rollback

## Journal

- 2026-04-27T12:03:26Z [implementation] — AC: 1.✓ _normalize() now always lowercases (was win32-only) — memory_pretool_block.py:42-46; 2.✓ Test asserts MEMORY/, Memory/, memory/, MeMoRy/ all blocked + non-memory paths still allowed; 3.✓ 8/8 tests pass; 4.✓ Negative — Linux/macOS .../MEMORY/x.md no longer slips through.
