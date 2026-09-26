---
slug: claude-md-keeps-custom-stacks-pointer
title: "CLAUDE.md потерял упоминание custom_stacks при укладке в 4096 байт"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: simple
role: tech-writer
stack: python
tier: trivial
call_budget: 6
defect_of: compaction-contract-lives-in-claude-md
scope: null
scope_exclude: null
relevant_files:
  - CLAUDE.md
  - "tests/test_stacks_extensible.py"
  - "tests/test_claude_md_size.py"
scope_paths:
  - CLAUDE.md
  - "tausik/tasks/claude-md-keeps-custom-stacks-pointer.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T15:49:22Z"
resolution: null
resolution_reason: null
---

## Goal

tests/test_stacks_extensible.py::TestDocsConsistency::test_claude_md_no_stale_count требует слова custom_stacks в CLAUDE.md; укладка раздела компакции в 4096 байт сократила строку Reference и убрала его. Тест не попал в scoped lane задачи компакции и всплыл в lane соседней задачи.

## Acceptance Criteria

AC-1: CLAUDE.md names custom_stacks in the Reference line and test_claude_md_no_stale_count is green. AC-2 (negative): the static portion stays ≤ 4096 bytes (test_claude_md_size) — bytes are paid by dropping the Quickstart pointer, not by dropping a rule. AC-3: focused pytest + signed verify.

## Plan

## Rollback

git revert одной строки.

## Journal

- 2026-09-12T15:45:32Z [implementation] — Root cause (regression): the compaction task paid for its CLAUDE.md bytes by shortening the Reference line and dropped the word custom_stacks that test_stacks_extensible pins; that test was outside the compaction task's scoped lane. Prevention: the pointer is back, bytes paid by dropping the Quickstart pointer (a link, not a rule); the full lane runs before the next commit.
- 2026-09-12T15:45:33Z [implementation] — AC verified: AC-1 ✓ 'custom_stacks' in the Reference line; test_claude_md_no_stale_count green. AC-2 ✓ Negative: static portion 4070 B ≤ 4096; no rule dropped (Quickstart pointer removed, quickstart stays linked from docs/README.md). AC-3 ✓ signed verify below.
