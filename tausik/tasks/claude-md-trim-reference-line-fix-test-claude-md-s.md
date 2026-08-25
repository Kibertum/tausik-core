---
slug: claude-md-trim-reference-line-fix-test-claude-md-s
title: "CLAUDE.md trim Reference line — fix test_claude_md_static_under_size_cap drift"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - CLAUDE.md
  - "tests/test_claude_md_size.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T20:04:25Z"
---

## Goal

CLAUDE.md static portion is 4113B, exceeds cap 4096B by 17 bytes (handoff #45 extended Reference line for T2.2 drift tests). Trim Reference line phrasing without losing the agent-contract.md pointer or the 3 drift-test anchors. Negative scenario: test_claude_md_static_under_size_cap MUST pass; test_claude_md_references_agent_contract MUST keep passing (the 'agent-contract.md' marker stays); the 3 drift-test phrases (estimation tier names, SENAR matrix, roles, custom_stacks, QG-2 mechanics) MUST still appear so they don't regress to failing.

## Acceptance Criteria

1. CLAUDE.md static portion (with DYNAMIC block stripped) measures ≤ 4096 bytes — verified by tests/test_claude_md_size.py::test_claude_md_static_under_size_cap PASS.
2. test_claude_md_references_agent_contract still PASS — the literal "agent-contract.md" pointer survives the trim.
3. Negative scenario / regression: the three T2.2 drift-test anchor phrases (estimation tiers like "trivial≤10", "SENAR matrix", "QG-2 mechanics") must still be present so we do not re-break the tests handoff #45 patched. If trimming forces a loss of any anchor, fall back to compressing whitespace / shortening connector words instead of dropping a phrase.
4. ruff green; tausik verify (CLI) green; full suite via pytest -m '' for the affected test file passes.
5. Bilingual CHANGELOG entry under Phase B Fixed: "CLAUDE.md size cap regression — Reference line tightened to 4096-byte budget without losing agent-contract.md pointer or drift-test anchors".

## Plan

## Rollback

## Journal

- 2026-05-03T20:04:25Z [implementation] — AC verified: 1.✓ static portion now 4096 bytes (was 4113); test_claude_md_static_under_size_cap PASS. 2.✓ test_claude_md_references_agent_contract PASS — 'agent-contract.md' pointer survives. 3.✓ Anchor keywords retained: estimation, SENAR matrix, roles, custom_stacks, QG-2 — see CLAUDE.md:64. 4.✓ Ruff All checks passed; CLI verify [PASS] pytest 0.5s. 5.✓ Bilingual CHANGELOG Phase B Fixed entry added.
