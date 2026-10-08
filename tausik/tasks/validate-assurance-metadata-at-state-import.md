---
slug: validate-assurance-metadata-at-state-import
title: "Validate assurance metadata at state import boundary"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: define-residual-assurance-contract
scope: "scripts/state_import.py, canonical assurance validation helpers if necessary, and aligned state import/export tests."
scope_exclude: "No change to valid state serialization format, unrelated task frontmatter, or database schema."
relevant_files:
  - "scripts/state_import.py"
  - "scripts/state_assurance_parse.py"
  - "tests/test_state_import.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:19:39Z"
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

Reject malformed assurance_profiles and assurance_impact before state import mutates the database.

## Acceptance Criteria

AC-1 import uses the canonical assurance validators. AC-2 scalar, mapping, unknown and duplicate profiles fail with a parse error before the transaction. AC-3 valid metadata round-trips. Negative: malformed metadata cannot reach task package, review or closure code.

## Plan

## Rollback

Revert the focused fix commit; retain the release block until a replacement fix passes review and verification.

## Journal

- 2026-10-04T12:19:25Z [implementation] — Root cause (missing-validation): git-state parse accepted assurance frontmatter without canonical validation, allowing malformed values into DB JSON columns and later KeyError paths. Prevention: decode the emitted JSON scalar and run assurance_policy validators during parse_tree before apply starts.
- 2026-10-04T12:19:35Z [implementation] — AC verified: AC-1 ✓ parse_tree decodes canonical impact JSON and calls validate_profiles/validate_impact before apply. AC-2 ✓ parametrized tests reject scalar, mapping, unknown, duplicate profiles and non-object impact with ParseError. AC-3 ✓ state import/export/task-package slice 69 passed and valid assurance round-trip remains byte-stable. Negative ✓ malformed metadata fails before import_tree transaction. Scoped critical verify #3475: 106 passed over 7/659 files.
