---
slug: controlled-prose-for-user-facing-answers
title: "Controlled prose for user-facing answers"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "bootstrap/bootstrap_templates.py, bootstrap/bootstrap_rules_upgrade.py, scripts/answer_shape.py, scripts/response_contract_audit.py, tests/test_response_contract_shape.py, tests/test_answer_rules_every_prompt.py, tests/test_instruction_tone.py, tests/test_caveman_output_mode.py, tests/test_response_contract_audit.py, AGENTS.md, CLAUDE.md, QWEN.md, docs/en/configuration.md, docs/ru/configuration.md, changelog.d/controlled-prose-answer-contract-111.md"
scope_exclude: "No full ASD-STE100 dictionary, certification claim, English-only enforcement, broad test expansion, HTML/video generation, commit, push, or release."
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_rules_upgrade.py"
  - "scripts/answer_shape.py"
  - "scripts/response_contract_audit.py"
  - "tests/test_response_contract_shape.py"
  - "tests/test_answer_rules_every_prompt.py"
  - "tests/test_instruction_tone.py"
  - "tests/test_caveman_output_mode.py"
  - "tests/test_response_contract_audit.py"
  - "tests/test_answer_shape_discipline.py"
  - AGENTS.md
  - CLAUDE.md
  - QWEN.md
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "changelog.d/controlled-prose-answer-contract-111.md"
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_rules_upgrade.py"
  - "scripts/answer_shape.py"
  - "scripts/response_contract_audit.py"
  - "tests/test_response_contract_shape.py"
  - "tests/test_answer_rules_every_prompt.py"
  - "tests/test_instruction_tone.py"
  - "tests/test_caveman_output_mode.py"
  - "tests/test_response_contract_audit.py"
  - AGENTS.md
  - CLAUDE.md
  - QWEN.md
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "changelog.d/controlled-prose-answer-contract-111.md"
  - "tests/test_answer_shape_discipline.py"
scope_tools: []
depends_on: []
completed_at: "2026-10-02T11:50:51Z"
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

Make ordinary TAUSIK answers easier to scan by shipping a small multilingual controlled-prose subset without claiming ASD-STE100 compliance or increasing the always-loaded instruction budget.

## Acceptance Criteria

AC-1 The canonical answer contract uses a multilingual controlled-prose subset: direct actor/action, active voice where natural, one action per sentence, one term per concept, and short paragraphs; it does not claim ASD-STE100 compliance. AC-2 The change replaces existing wording and keeps the always-loaded answer block at or below its current 776-character ceiling and within minimal-tier budgets. AC-3 User language, byte-exact code/tool output, and full SENAR evidence remain unchanged. Negative: the formatter/rules never simplify code, commands, paths, errors, AC evidence, decisions, or necessary technical terms.

## Plan

[{"step": "Measure the current answer contract and identify wording that can be replaced, not appended", "done": true}, {"step": "Define the multilingual controlled-prose subset and protected-content boundary", "done": true}, {"step": "Update the canonical rules and response audit with the fewest behavioral tests", "done": true}, {"step": "Verify generated consumer rules and token ceilings on the affected lane", "done": true}]

## Rollback

Restore the previous answer-contract wording and regenerate consumer rules; no data migration.

## Journal

- 2026-10-02T11:33:14Z [planning] — User specification: make framework answers more systematic and easier to understand; borrow the useful constraints shown in Karpathy's ASD-STE100 example, but preserve multilingual technical accuracy and the 1.11 token objective. Prefer replacement over new always-loaded prose; keep protected evidence complete.
- 2026-10-02T11:43:32Z [implementation] — Defined the controlled-prose subset and protected-content boundary.
- 2026-10-02T11:43:32Z [implementation] — Measured the existing 776-character contract and identified replacement budget.
- 2026-10-02T11:43:32Z [implementation] — Step 1 done: measured the canonical block at its binding 776-character ceiling. Replaced wording instead of appending a second style layer; protected evidence classes and answer order remain.
- 2026-10-02T11:43:32Z [implementation] — Step 2 done: defined multilingual controlled prose—named actor/action, natural active voice, one action per sentence, one term per concept, short paragraphs; explicit no-ASD-STE100 claim.
- 2026-10-02T11:45:25Z [implementation] — Step 3 done: canonical and per-prompt rules now carry controlled prose at 773 chars (3 fewer). Exact legacy blocks upgrade safely; custom blocks remain untouched. Added two behavioral test nodes; focused lane 93 passed. Audit explicitly refuses fake multilingual compliance scoring.
- 2026-10-02T11:45:25Z [implementation] — Updated rules, safe consumer upgrade, docs, audit boundary, and two compact behavioral checks.
- 2026-10-02T11:50:23Z [implementation] — Step 4 done: host-focused set 185 passed; scoped verify #3370 PASS with 1057 passed, 12 skipped, 8 deselected across 41/657 mapped files. Canonical/per-prompt blocks are byte-equal at 773 chars; generated Claude/Codex, Cursor, Qwen and OpenCode rules carry the clause. Test discipline set shrank 6→1 nodes.
- 2026-10-02T11:50:23Z [implementation] — Verified consumer upgrades, byte ceiling, focused host paths, and scoped affected lane.
- 2026-10-02T11:50:32Z [implementation] — AC-1 (multilingual controlled prose, no compliance claim): ✓ tests/test_response_contract_shape.py::test_controlled_prose_is_multilingual_guidance_not_a_compliance_claim AC-2 (no prefix growth): ✓ tests/test_response_contract_shape.py::test_the_ceiling_is_the_measured_size_not_a_round_number — 773≤776 AC-3 (language, byte-exact and full evidence preserved): ✓ tests/test_response_contract_shape.py::test_the_keep_lists_survived_the_rewrite and tests/test_answer_rules_every_prompt.py::test_the_injected_rules_are_the_shipped_rules_byte_for_byte Negative (custom blocks and protected content untouched): ✓ tests/test_response_contract_shape.py::test_existing_rules_upgrade_only_the_exact_legacy_contract Scoped verification: green verification_run #3370; 1057 passed, 12 skipped, 8 deselected, 41/657 files.
- 2026-10-02T11:50:47Z [implementation] — AC-1 controlled prose and no-compliance boundary verified by tests/test_response_contract_shape.py::test_controlled_prose_is_multilingual_guidance_not_a_compliance_claim. AC-2 contract is 773 characters, below the former 776 ceiling. AC-3 protected content and byte parity verified. Negative: exact legacy blocks upgrade; custom blocks remain untouched. Domain: generated Claude/Codex, Cursor, Qwen and OpenCode rules all carry the new clause. Verification_run #3370 passed 1057 tests over 41 of 657 mapped files.
