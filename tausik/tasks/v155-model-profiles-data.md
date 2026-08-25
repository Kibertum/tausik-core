---
slug: v155-model-profiles-data
title: "Model profiles as data + family-agnostic flagship tier (axis-2)"
status: done
epic: v155-kilo-zai
story: v155-provider-abstraction
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/model_profiles.py (new), scripts/model_routing_matrix.py, scripts/model_routing.py"
scope_exclude: "scripts/providers/* (done), bootstrap/*, tests/* (next task), docs/*"
relevant_files:
  - "scripts/model_profiles.py"
  - "scripts/model_routing_matrix.py"
  - "scripts/model_routing.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T08:21:49Z"
---

## Goal

Move _TIER_SPEC / _PROFILE_SLUG_BY_MODEL_ID from code to model_profiles data in .tausik/config.json; add a GLM family; make the routing matrix emit the flagship-of-active-family tier instead of hardcoded claude ids, so GLM models route without code changes. Claude behaviour unchanged when no profiles override.

## Acceptance Criteria

1. New scripts/model_profiles.py provides families (claude+glm), load_families(config) merge, reverse_index, vendor_of, rank_of, spec_for. 2. suggest_model gains family param; family=None defaults to claude → ALL existing test_model_routing assertions unchanged (same claude ids). 3. suggest_model(family='glm') for (implement,complex) resolves to a GLM model id, not a claude id. 4. format_task_start_banner infers family from the active model (glm-* → glm) and recommends within that family; falls back to config model_profiles.default_family then claude. 5. Banner: when normalized active id == recommended id → '✓ model match' regardless of rank arithmetic. 6. _model_tier resolves a GLM id's rank via profiles (verdict no longer treats glm-* as unknown). 7. ruff+mypy clean, filesize gate green (matrix stays <400 lines). NEGATIVE: load_families on malformed/missing config returns defaults without raising; suggest_model(family='nonexistent') falls back to claude rank (no KeyError); vendor_of(None)/rank_of('') return None.

## Plan

## Rollback

git checkout scripts/model_routing_matrix.py scripts/model_routing.py && rm scripts/model_profiles.py — isolated additive change; defaults preserve prior claude-only behaviour.

## Journal

- 2026-06-19T08:21:13Z [implementation] — Added scripts/model_profiles.py (families×ranks data, load_families/vendor_of/rank_of/spec_for/default_family). matrix: _TIER_SPEC now references DEFAULT_FAMILIES[claude] (no drift), suggest_model+family param, _model_tier+optional families. banner: infers family from active model (glm-*→glm), default_family fallback, same-id match short-circuit, passes families to _model_tier. Smoke: claude default unchanged (claude-opus-4-8); glm family→glm-4.6; default_family=glm works w/o detection; glm-4.5-air on complex→mismatch; negatives return None/defaults. 104 routing tests pass, ruff+mypy clean, matrix 300L.
- 2026-06-19T08:21:24Z [implementation] — AC1 ✓ model_profiles.py: families(claude+glm), load_families, reverse_index, vendor_of, rank_of, spec_for, default_family. AC2 ✓ family=None→claude; 104 routing tests pass unchanged (same claude ids). AC3 ✓ suggest_model(family='glm') complex implement → glm-4.6. AC4 ✓ banner infers glm from active glm-* and recommends GLM; default_family=glm fallback verified w/o detection. AC5 ✓ active id==rec id → '✓ model match' (glm-4.6 case). AC6 ✓ _model_tier('glm-4.6',fams)=3, =None without fams (back-compat). AC7 ✓ ruff+mypy clean, matrix 300L<400. NEG ✓ load_families('x')→defaults; family='zzz'→claude fallback (no KeyError); vendor_of(None)/rank_of('')→None. Domain: a z.ai/GLM session (Anthropic-compatible transcript, model=glm-4.6) now routes to GLM models and gets correct under/over-powered verdicts — the real user workflow.
- 2026-06-19T08:21:48Z [implementation] — AC1-7 + negatives all verified (see prior log). Knowledge: pattern Memory #177 (capability-rank matrix × vendor-family data, same-id match short-circuit). Domain: a z.ai/GLM session (Anthropic-compatible transcript, model=glm-4.6) now routes to GLM models with correct verdicts — the real user workflow. 104 routing tests pass, ruff+mypy clean, matrix 300L<400.
