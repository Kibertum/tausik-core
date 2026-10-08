---
slug: prune-a-second-low-value-test-tranche
title: "Prune a second low-value test tranche"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: null
defect_of: null
scope: "Consolidate low-value documentation and changelog test families; propagate concise behavioral-test discipline through shared host templates and upgrade reconciliation."
scope_exclude: "Security, auth, hooks, task lifecycle, migrations, evidence integrity, upgrade/restore behavior, r111 replay status, commits, pushes, releases."
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_rules_upgrade.py"
  - "scripts/affected_test_selection.py"
  - "tests/test_affected_test_selection.py"
  - "tests/test_claude_md_size.py"
  - "tests/test_changelog_fragments.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_opencode_bootstrap.py"
  - AGENTS.md
  - CLAUDE.md
  - QWEN.md
  - "changelog.d/prune-a-second-low-value-test-tranche.md"
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_rules_upgrade.py"
  - "tests/test_claude_md_size.py"
  - "tests/test_changelog_fragments.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_opencode_bootstrap.py"
  - "docs/en/testing-principles.md"
  - "docs/ru/testing-principles.md"
  - "changelog.d/prune-a-second-low-value-test-tranche.md"
  - AGENTS.md
  - CLAUDE.md
  - ".cursorrules"
  - QWEN.md
  - ".opencode/tausik-rules.md"
  - "scripts/affected_test_selection.py"
  - "tests/test_affected_test_selection.py"
scope_tools: []
depends_on: []
completed_at: "2026-10-02T11:17:56Z"
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

Cut execution and maintenance cost in selected low-value test families by at least 2x while preserving each distinct observable behavior, and make the no-test-for-test-count rule explicit in generated consumer guidance.

## Acceptance Criteria

AC-1 Selected test families shrink by at least 2x in collected pytest nodes while every retained product contract has a named surviving behavioral assertion. AC-2 No public contract, security negative, lifecycle, migration, evidence-integrity, upgrade, or restore coverage is removed; malformed-input refusals remain exercised. AC-3 Fresh and upgraded generated host rules tell agents to avoid tests prompted only by file changes, reuse existing behavioral coverage, and consolidate redundant cases. AC-4 Focused tests, pytest dedupe audit, scoped verify, default release lane, and slow release lane pass; before/after nodes, executed/deselected counts, and runtime are recorded. Negative: malformed changelog fragments and non-UTF8 existing host rules remain refused/preserved, never silently rewritten.

## Plan

[{"step": "Measure selected families and map every behavior to a survivor", "done": true}, {"step": "Consolidate repeated setup and editorial assertions without dropping boundaries", "done": true}, {"step": "Propagate concise test discipline through fresh and upgraded host rules", "done": true}, {"step": "Run focused, dedupe, scoped verify, and release lanes; record evidence", "done": true}]

## Rollback

Revert this task's test consolidations and template/reconciler edits; regenerate host rules.

## Journal

- 2026-10-02T11:04:06Z [implementation] — AC-1 baseline: tests/test_claude_md_size.py + tests/test_changelog_fragments.py collected 31 nodes and passed in 3.41s wall. Contracts mapped before edit: implicit-file byte/headroom and navigation; fragment ownership/bilingual refusal; deterministic destructive/idempotent assembly; dry-run; atomic malformed refusal; live gate route; stdlib-only dependency. After consolidation: 10 nodes (3.1x fewer), focused family passes.
- 2026-10-02T11:04:06Z [implementation] — AC-3: shared bootstrap keeps the existing fresh-project behavioral rule and upgrades preserved CLAUDE.md, AGENTS.md, Cursor, Qwen and OpenCode files once with a canonical Test discipline block. Existing tests now assert CRLF/idempotence/user prose and non-UTF8 preservation without adding test nodes. Normal bootstrap upgraded this repository across supported hosts.
- 2026-10-02T11:04:07Z [implementation] — Consolidated repeated setup and implementation-string checks to 10 behavioral nodes.
- 2026-10-02T11:04:07Z [implementation] — Fresh and upgraded host rules now carry concise no-test-for-file-change discipline.
- 2026-10-02T11:04:07Z [implementation] — Measured 31 nodes/3.41s and mapped each retained observable boundary.
- 2026-10-02T11:17:51Z [implementation] — AC-1: ✓ tests/test_claude_md_size.py and tests/test_changelog_fragments.py collect 10 nodes versus baseline 31 (3.1x fewer; -21, 67.7%). Surviving checks cover byte/headroom+navigation, valid/invalid fragments, ordered destructive/idempotent assembly, dry-run, atomic refusal, live gate route and dependency boundary.
- 2026-10-02T11:17:51Z [implementation] — AC-2: ✓ tests/test_changelog_fragments.py::test_incomplete_or_ambiguous_fragments_are_all_refused and ::test_malformed_input_stops_assembly_before_any_write retain malformed/missing/duplicate/half-language negatives; ::test_continuous_changelog_gate_accepts_a_valid_fragment exercises the real gate instead of exact source strings. No security/lifecycle/migration/evidence/restore test was removed.
- 2026-10-02T11:17:52Z [implementation] — AC-3: ✓ tests/test_bootstrap_generate.py::test_generator_preserves_existing_and_adds_answer_contract_once and tests/test_opencode_bootstrap.py::TestRulesFile::test_rules_file_carries_the_shared_body verify fresh behavioral guidance plus idempotent upgrade of custom rules. Equivalent existing AGENTS/Cursor/Qwen/OpenCode discipline is detected instead of duplicated; non-UTF8 preservation remains covered.
- 2026-10-02T11:17:52Z [implementation] — AC-4: ✓ focused 75 passed in 4.19s; dedupe audit 0 copy / 282 parallel; scoped verify #3362 PASS, 676 passed, 8 deselected, 34/657 files; default release lane 12780 passed, 34 skipped, 143 deselected in 124.43s; slow lane 143 passed, 12814 deselected in 125.33s. First default run exposed and fixed a type inference regression in scripts/affected_test_selection.py; mypy and 24 focused regression tests pass.
- 2026-10-02T11:17:52Z [implementation] — Focused, dedupe, scoped verify #3362, default and slow release lanes passed with counts recorded.
