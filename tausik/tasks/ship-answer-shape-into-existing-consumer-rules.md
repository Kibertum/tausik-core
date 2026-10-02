---
slug: ship-answer-shape-into-existing-consumer-rules
title: "Ship answer shape into existing consumer rules"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "Canonical answer-shape upgrade reconciliation in existing host rule files, existing cross-host tests, current root rules and concise changelog/docs."
scope_exclude: "No model prompt hook expansion, no answer-content enforcement gate, no rewrite of user prose, no paid benchmark, commit, push or release."
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_rules_upgrade.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_opencode_bootstrap.py"
  - "tests/test_answer_rules_every_prompt.py"
  - "tests/test_answer_shape_discipline.py"
  - CLAUDE.md
  - AGENTS.md
  - "changelog.d/answer-shape-existing-projects-111.md"
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_opencode.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_answer_rules_every_prompt.py"
  - "tests/test_answer_shape_discipline.py"
  - CLAUDE.md
  - AGENTS.md
  - "changelog.d/answer-shape-existing-projects-111.md"
  - "tests/test_opencode_bootstrap.py"
  - "bootstrap/bootstrap_rules_upgrade.py"
scope_tools: []
depends_on: []
completed_at: "2026-10-02T10:54:13Z"
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

Ensure every fresh or upgraded TAUSIK project gives supported agents the concise done-verified-left-call response contract without requiring a skill invocation.

## Acceptance Criteria

AC-1 Existing CLAUDE, AGENTS, Cursor, Qwen and OpenCode rule files gain exactly one canonical answer-shape block while preserving user prose. AC-2 Fresh generation remains byte-consistent across hosts and repeated bootstrap is idempotent. AC-3 The framework's own CLAUDE.md and AGENTS.md both carry the contract. AC-4 NEGATIVE: no new test file or per-host copy; consolidate existing tests and reduce duplicate coverage.

## Plan

[{"step": "Define an idempotent upgrade rule that preserves user prose", "done": true}, {"step": "Apply the canonical block through every existing host generator", "done": true}, {"step": "Consolidate existing cross-host tests without growing the suite", "done": true}, {"step": "Redeploy, run focused verification and record the consumer guarantee", "done": true}]

## Rollback

Revert answer-shape reconciliation and restore exact-preserve bootstrap behavior; remove the injected root AGENTS block and changelog fragment.

## Journal

- 2026-10-02T10:51:08Z [implementation] — Defined one upgrade rule: preserve existing UTF-8 bytes, insert the canonical answer block before DYNAMIC when present or append otherwise, refuse non-UTF8, and become a no-op after first write.
- 2026-10-02T10:51:09Z [implementation] — Consolidated existing tests: fresh/upgrade/idempotence/user-prose cases cover all generators; root CLAUDE+AGENTS share one loop; removed one duplicate vendored-skill test. Net pytest nodes -1, no new test file, focused 104 passed, dedupe audit has no group involving changed tests.
- 2026-10-02T10:51:09Z [implementation] — Every existing rules generator already calls the shared bootstrap_templates seam; enhancing that single seam reaches Claude, AGENTS/Codex/Kilo, Cursor, Qwen and OpenCode without host copies.
- 2026-10-02T10:54:09Z [implementation] — AC-1: ✓ existing Claude/AGENTS/Cursor/Qwen/OpenCode generator tests preserve the original byte prefix and add one canonical block; Kilo/Codex share AGENTS. AC-2: ✓ repeated calls remain one block and CRLF stays CRLF; fresh bodies still use ANSWER_SHAPE. AC-3: ✓ tests/test_answer_rules_every_prompt.py checks both root CLAUDE.md and AGENTS.md. AC-4 NEGATIVE: ✓ no new test file; one duplicate vendored-skill test removed, net pytest nodes -1; changed tests appear in no dedupe group. Domain: normal bootstrap --ide all visibly upgraded legacy AGENTS/Cursor/OpenCode rules, and scoped verify #3358 passed 653 tests.
- 2026-10-02T10:54:09Z [implementation] — Redeployed all hosts; live AGENTS, Cursor and OpenCode legacy files received one block; second generator pass was hash-identical. Focused 114 passed; scoped verify #3358 passed 653 with 8 deselected.
