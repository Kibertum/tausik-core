---
slug: preserve-custom-rules-on-profile-conversion
title: "Preserve customized host rules during governance profile conversion"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "bootstrap/bootstrap_governance.py and directly aligned bootstrap governance tests"
scope_exclude: "No change to generated rule content outside ownership and preservation behavior"
relevant_files:
  - "bootstrap/bootstrap_governance.py"
  - "tests/test_rules_generator_warning_parity.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_bootstrap_real.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:52:12Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Prevent bootstrap profile conversion from truncating user-customized CLAUDE.md or AGENTS.md content.

## Acceptance Criteria

AC-1 ambiguous or customized legacy rule files are preserved or refused with an actionable warning. AC-2 only verifiably owned pristine generated files may be fully replaced. AC-3 memory-only conversion keeps custom text. Negative: no silent custom-content deletion.

## Plan

## Rollback

Revert bootstrap ownership detection and aligned tests.

## Journal

- 2026-10-04T12:51:48Z [implementation] — Focused verification: ruff passed and 35 bootstrap/rules tests passed; regressions preserve customized legacy and stamped files, refresh pristine stamped files, and tolerate expected dynamic-state updates.
- 2026-10-04T12:51:48Z [implementation] — Root cause (missing-validation): familiar headings, dynamic markers, or profile markers were treated as proof that the whole rules file remained generator-owned, although users could add custom instructions after generation. Prevention: stamp the static generated payload, ignore only the mutable dynamic block, and overwrite solely when that ownership hash still matches.
- 2026-10-04T12:52:08Z [implementation] — ✓ AC-1 ambiguous legacy or modified rule files are preserved and emit an actionable warning. ✓ AC-2 only a file with a matching static ownership SHA-256 is replaced. ✓ AC-3 memory-only conversion preserves custom production instructions. ✓ Negative: profile markers and familiar headings alone cannot authorize whole-file deletion. Domain: the ownership hash excludes only the runtime-managed dynamic state block, so normal session updates do not create false customization.
- 2026-10-04T12:52:19Z [done] — AC-1: ✓ tests/test_rules_generator_warning_parity.py::TestGeneratedRulesOwnership::test_customized_legacy_rules_are_preserved_on_profile_switch. AC-2: ✓ tests/test_rules_generator_warning_parity.py::TestGeneratedRulesOwnership::test_pristine_owned_rules_can_be_refreshed and ::test_custom_text_invalidates_the_ownership_stamp. AC-3: ✓ memory-only regression above. Negative: ✓ tests/test_rules_generator_warning_parity.py::TestGeneratedRulesOwnership::test_dynamic_state_updates_do_not_break_static_ownership. Verify: ✓ verification_run #3482 passed 35 tests, 4 deselected, 8 gates passed, hadolint not applicable.
