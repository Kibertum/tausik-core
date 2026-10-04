---
slug: align-review-and-bootstrap-documentation
title: "Align review and bootstrap documentation"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Configuration documentation and review skill routing guidance."
scope_exclude: "Runtime behavior and unrelated release documentation."
relevant_files:
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/cli-quality.md"
  - "docs/ru/cli-quality.md"
  - "harness/skills/review/SKILL.md"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:43:58Z"
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

Make English and Russian configuration docs and review skill guidance match enforced 1.11.1 behavior.

## Acceptance Criteria

AC-1: English and Russian configuration docs distinguish pristine stamped refreshes from customized or legacy preservation. AC-2: Review guidance requires a different model for L3 and classifies same-model fresh-context review as L2. AC-3 negative: No documentation claims that all context/output changes avoid rewrites or that separate context alone qualifies as L3. AC-4: documentation checks pass.

## Plan

## Rollback

Revert the documentation corrections.

## Journal

- 2026-10-04T13:43:39Z [implementation] — AC-1: English/Russian configuration docs now state that only pristine stamped rules refresh and that custom/legacy files remain untouched. AC-2: review skill and bilingual CLI docs require a different model family for L3 and classify fresh same-family context as L2. AC-3: ✓ repository search finds none of the superseded no-rewrite or separate-context-L3 claims. AC-4: ✓ scripts/hooks/check_docs.py passed; docs_lint reported only two pre-existing publishing-history warnings. Domain: operator guidance now matches enforcement.
- 2026-10-04T13:43:54Z [implementation] — AC-1: ✓ bilingual configuration docs distinguish pristine stamped refreshes from custom/legacy preservation. AC-2: ✓ review skill and bilingual CLI docs require different-model L3 and classify same-family fresh context as L2. AC-3: ✓ repository search found none of the superseded claims. AC-4: ✓ scripts/hooks/check_docs.py passed and verify #3508 passed 6 applicable gates; ruff, hadolint, pytest skipped because the scope contains no supported source/tests. Domain: published workflow guidance matches runtime enforcement.
