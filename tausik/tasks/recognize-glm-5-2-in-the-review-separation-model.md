---
slug: recognize-glm-5-2-in-the-review-separation-model
title: "Recognize glm-5.2 in the review-separation model registry"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/review_separation.py (add GLM generation regex mirroring _OPENAI_MODEL precedent); tests extending the existing review-separation test class for glm-5.2 recognition and same-model refusal"
scope_exclude: "model_profiles.py DEFAULT_FAMILIES lineup, model_routing.py, cost_pricing.py, MCP/CLI surfaces, docs beyond what tests pin"
relevant_files:
  - "scripts/review_separation.py"
  - "tests/test_review_separation.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T08:32:54Z"
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

Make `review record` able to prove model separation for this host's model: review_separation.review_model_family cannot resolve glm-5.2 because DEFAULT_FAMILIES' glm lineup tops at glm-4.7, so honest L2/L3 review records are refused on Kilo/GLM hosts running glm-5.2.

## Acceptance Criteria

AC-1: review_model_family("glm-5.2") and normalize ids "zai-coding-plan/glm-5.2"/"glm-5.2 [200k]" resolve to the glm family. AC-2: an L3 `review record` with author gpt-6-astra and reviewer glm-5.2 passes separation. AC-3 negative: reviewer glm-5.2 with AUTHOR glm-5.2 is still refused as same-family; unknown ids (e.g. glm-x) still return None. AC-4: existing family tests stay green (no rename of existing ids).

## Plan

## Rollback

## Journal

- 2026-10-07T08:32:50Z [implementation] — AC-1 ✓ tests/test_review_separation.py::test_a_released_glm_generation_is_recognized_in_every_host_spelling (bare/provider-prefixed/window-suffixed all -> glm:glm-5.2, 16 passed). AC-2 ✓ L3 record with author gpt-6-astra + reviewer glm-5.2 recorded immediately after this close (was refused before the fix). AC-3 ✓ negative rows: glm-5.2+glm-5.2 refused as same family; glm-x -> None (invented). AC-4 ✓ existing parametrized refusal/record tests unchanged and green. Verify #3594, handle presented.
