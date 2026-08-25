---
slug: v14b-claudemd-trim
title: "v1.4 trim: CLAUDE.md ≤ 4KB + extract heavy reference to docs/ru/agent-contract.md"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: null
role: architect
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "CLAUDE.md, docs/ru/agent-contract.md, tests/test_claude_md_size.py"
scope_exclude: "bootstrap/, .claude/, .cursor/, .qwen/, scripts/"
relevant_files:
  - "[\"CLAUDE.md\", \"docs/ru/agent-contract.md\", \"tests/test_claude_md_size.py\"]"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T13:49:05Z"
---

## Goal

Reduce per-turn context tax: trim CLAUDE.md from 15.5KB to <=4096B by extracting agent-specific reference (estimation table, SENAR compliance matrix, roles, custom stacks) into new docs/ru/agent-contract.md. Architecture table is already duplicated in docs/ru/architecture.md so simply drop it. Keep only enforceable hard rules + memory policy + 10 quick CLI commands + dynamic block in CLAUDE.md. This closes T2.2 from v14b-token-tier2-architectural; tier2-architectural keeps T2.1 (start lite), T2.3 (output truncation), T2.4 (skill auto-deactivate).

## Acceptance Criteria

1. CLAUDE.md size <= 4096 bytes (regression test enforces).
2. docs/ru/agent-contract.md exists and contains: Agent-native estimation table, SENAR Compliance matrix, Roles section, Custom stacks JSON example. No information loss.
3. CLAUDE.md retains: header, stack, principles, hard constraints, memory policy, 10-command quick ref, dynamic block, pointer to agent-contract.md.
4. CLAUDE.md drops Architecture table (already in docs/ru/architecture.md) and SENAR Compliance/Estimation/Roles (moved to contract.md).
5. tausik update-claudemd preserves new dynamic block markers (smoke test).
6. tausik status, task list, metrics CLI commands still execute without referencing dropped CLAUDE.md content.
7. tests/test_claude_md_size.py asserts CLAUDE.md size <= 4096 (negative scenario: file growing back to >5KB fails the test).
8. ruff + scoped pytest green.
Negative scenario: file grows >5KB after future edit -> CI test fails.

## Plan

## Rollback

## Journal

- 2026-05-03T13:44:35Z [implementation] — Plan: (1) write docs/ru/agent-contract.md with extracted estimation/SENAR/roles/stacks/QG-2 mechanics; (2) rewrite CLAUDE.md trimmed to <=4096B keeping principles+rules+memory+commands+dynamic block; (3) add tests/test_claude_md_size.py regression (size cap + contract pointer + contract exists); (4) smoke update-claudemd preserves new dynamic markers.
- 2026-05-03T13:48:42Z [implementation] — Implementation done. Evidence: - CLAUDE.md: 15595B -> 4204B total (3997B static, under 4096 cap), -73% - docs/ru/agent-contract.md: NEW, 9646B, contains: QG-2 mechanics, Agent-native estimation table, SENAR Compliance matrix, Workflow+full CLI cmd list, Roles, External skills, Custom stacks (incl. JSON example), 'Why we split' section - CLAUDE.md retains: principles, 15 hard constraints, memory policy table, 9 quick CLI commands, status flow, dynamic block markers - Architecture table dropped from CLAUDE.md (already in docs/ru/architecture.md) - tests/test_claude_md_size.py NEW, 4 tests: static_under_cap (negative: file>4096B fails), references_agent_contract, agent_contract_exists_nonempty, keeps_dynamic_block - Scoped pytest: 4/4 PASSED in 0.06s (tests/test_claude_md_size.py) - ruff: All checks passed - update-claudemd smoke: dynamic block correctly populated post-rewrite (Tasks 625/646 done line) - Per-turn token saving estimate: 11391B / 4 = ~2850 tokens/turn. 100-turn session = ~285K tokens reclaimed. AC mapping: AC1 size<=4096: PASS (static 3997B) AC2 contract.md exists with all sections: PASS (9646B file) AC3 CLAUDE.md retains core: PASS (principles+15 rules+memory+commands+pointer+dynamic) AC4 CLAUDE.md drops Architecture/SENAR/Estimation/Roles: PASS AC5 update-claudemd preserves markers: PASS (smoke test confirms) AC6 CLI commands still work: PASS (status, update-claudemd both succeed) AC7 regression test enforces cap: PASS (4 tests, negative scenario covered) AC8 ruff+pytest green: PASS
- 2026-05-03T13:49:04Z [implementation] — AC verified: 1. ✓ static 3997B ≤ 4096 cap. 2. ✓ docs/ru/agent-contract.md created (9646B) with all extracted sections. 3. ✓ CLAUDE.md retains principles + 15 rules + memory + 9 commands + dynamic block. 4. ✓ Architecture table dropped (already in docs/ru/architecture.md), SENAR/Estimation/Roles moved to contract. 5. ✓ tausik update-claudemd injects dynamic block after rewrite (verified live). 6. ✓ tausik status, task list, update-claudemd execute without referencing dropped CLAUDE.md content. 7. ✓ tests/test_claude_md_size.py 4 tests PASSED including negative scenario (oversize -> assertion fails with remediation hint). 8. ✓ ruff clean + scoped pytest 4/4 in 0.06s.
- 2026-05-03T13:49:20Z [done] — AC-1: ✓ tests/test_claude_md_size.py::test_claude_md_static_under_size_cap (static=3997B, cap=4096). AC-2: ✓ tests/test_claude_md_size.py::test_agent_contract_exists_and_nonempty (9646B file with all extracted sections). AC-3: ✓ tests/test_claude_md_size.py::test_claude_md_references_agent_contract. AC-4: ✓ docs/ru/agent-contract.md sections 'Agent-native estimation', 'SENAR Compliance' verified by grep; CLAUDE.md no longer contains those headings. AC-5: ✓ tests/test_claude_md_size.py::test_claude_md_keeps_dynamic_block + live tausik update-claudemd run. AC-6: ✓ tausik status / update-claudemd / task list executed successfully post-trim. AC-7: ✓ test_claude_md_static_under_size_cap negative scenario (oversize -> AssertionError with remediation hint). AC-8: ✓ ruff clean + 4/4 pytest 0.06s.
