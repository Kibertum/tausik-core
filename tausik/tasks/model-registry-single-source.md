---
slug: model-registry-single-source
title: "Model rank↔id: derive routing reverse-map from model_profiles (kill the unguarded triplicate)"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/model_routing_matrix.py (derive _PROFILE_SLUG_BY_MODEL_ID); tests/test_model_routing.py or new test asserting derivation; CHANGELOG.md + CHANGELOG.ru.md"
scope_exclude: "scripts/cost_pricing.py::_MODEL_PRICING (distinct pricing concern, already drift-guarded — do NOT collapse); scripts/model_profiles.py DEFAULT_FAMILIES data (source of truth, unchanged); model_routing.py public API"
relevant_files:
  - "scripts/model_routing_matrix.py"
  - "tests/test_model_routing.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T12:54:57Z"
---

## Goal

Make model_profiles.DEFAULT_FAMILIES the single source of truth for the Claude rank↔id mapping. model_routing_matrix._PROFILE_SLUG_BY_MODEL_ID currently hand-restates that mapping with no drift guard; derive it from profiles instead so a point-release bump propagates for free and can never drift. cost_pricing._MODEL_PRICING stays as-is (distinct pricing concern, already mechanically drift-guarded) — reducing it would add coupling.

## Acceptance Criteria

1. model_routing_matrix._PROFILE_SLUG_BY_MODEL_ID is DERIVED from model_profiles.DEFAULT_FAMILIES['claude'] (reverse_index), not a hand-written literal. 2. A new test asserts the derived map equals the reverse of DEFAULT_FAMILIES['claude'] AND that a point-release id (e.g. claude-opus-4-9) still resolves via _model_id_to_profile_slug's family fallback — proving no re-hardcoding needed. 3. _model_id_to_profile_slug behaviour unchanged for all previously-mapped ids (opus-4-7/4-8, sonnet-4-6, haiku-4-5, fable-5 → correct slug). 4. cost_pricing.routed_claude_model_ids still satisfies its guard tests. 5. Full pytest suite green, 0 warnings. 6. CHANGELOG EN+RU entry documenting the single-source derivation AND the explicit decision to leave cost_pricing._MODEL_PRICING as a distinct guarded concern. NEGATIVE/BOUNDARY: 7. An unrecognised id with no family token and absent from profiles (e.g. 'glm-4.6', 'mystery-9') → _model_id_to_profile_slug returns None — never a silent wrong-slug guess; empty/None input → None.

## Plan

## Rollback

git revert the commit — restores the hand-written _PROFILE_SLUG_BY_MODEL_ID literal. Pure refactor, no schema/data change, no migration.

## Journal

- 2026-07-26T12:39:55Z [implementation] — Derived _PROFILE_SLUG_BY_MODEL_ID from model_profiles.DEFAULT_FAMILIES['claude'] via reverse_index (was a hand-written literal). Added TestProfileSlugSingleSource (derivation guard + point-release-bump proof + slug-resolution parity + negative None cases). cost_pricing._MODEL_PRICING left as distinct guarded concern per scope_exclude. CHANGELOG EN+RU added. Targeted run: 113 passed.
- 2026-07-26T12:53:03Z [implementation] — AC verified: 1. ✓ _PROFILE_SLUG_BY_MODEL_ID now = _derive_profile_slug_by_model_id() reverse-indexed from model_profiles.DEFAULT_FAMILIES['claude']; no literal remains (model_routing_matrix.py) 2. ✓ tests/test_model_routing.py::TestProfileSlugSingleSource::test_registry_is_the_reverse_of_default_families + test_derivation_tracks_a_hypothetical_point_release_bump (opus 4-8→4-9 propagates, old id drops) 3. ✓ test_slug_resolution_unchanged parametrized: opus-4-7/4-8/4-9, sonnet-4-6, haiku-4-5, fable-5, normalized case+suffix all resolve to correct slug 4. ✓ tests/test_cost_pricing.py 113 passed incl TestPricingCoverage.test_every_routed_claude_model_has_a_price + test_the_guard_reads_the_real_routing_tables 5. ✓ full suite 5954 passed 24 skipped 0 warnings; single drift (constants test_count) regenerated → test_check_docs_hook 6 passed 6. ✓ CHANGELOG.md + CHANGELOG.ru.md Unreleased entries documenting derivation AND the explicit decision to leave cost_pricing._MODEL_PRICING distinct/guarded 7. ✓ test_unrecognised_id_returns_none: glm-4.6, mystery-9, '', None → _model_id_to_profile_slug returns None (no wrong-slug guess)
- 2026-07-26T12:53:30Z [implementation] — AC verified: 1. ✓ _PROFILE_SLUG_BY_MODEL_ID now = _derive_profile_slug_by_model_id() reverse-indexed from model_profiles.DEFAULT_FAMILIES['claude']; no literal remains 2. ✓ TestProfileSlugSingleSource::test_registry_is_the_reverse_of_default_families + test_derivation_tracks_a_hypothetical_point_release_bump 3. ✓ test_slug_resolution_unchanged: opus-4-7/4-8/4-9, sonnet-4-6, haiku-4-5, fable-5, normalized case+suffix 4. ✓ test_cost_pricing.py 113 passed incl coverage guard tests 5. ✓ full suite 5954 passed 24 skipped 0 warnings; constants test_count drift regenerated → test_check_docs_hook 6 passed 6. ✓ CHANGELOG.md + CHANGELOG.ru.md document derivation + explicit decision to leave cost_pricing._MODEL_PRICING distinct 7. ✓ test_unrecognised_id_returns_none: glm-4.6, mystery-9, '', None → None
- 2026-07-26T12:54:55Z [implementation] — AC verified: 1. ✓ _PROFILE_SLUG_BY_MODEL_ID = _derive_profile_slug_by_model_id() reverse-indexed from model_profiles.DEFAULT_FAMILIES['claude']; literal removed 2. ✓ TestProfileSlugSingleSource: registry==reverse(DEFAULT_FAMILIES) + point-release-bump 4-8→4-9 propagates 3. ✓ test_slug_resolution_unchanged: opus-4-7/4-8/4-9, sonnet-4-6, haiku-4-5, fable-5, case+suffix 4. ✓ test_cost_pricing.py 113 passed incl coverage guard 5. ✓ full suite 5954 passed/24 skipped/0 warn; constants test_count regenerated 6106→6119; test_check_docs_hook 6 passed 6. ✓ CHANGELOG EN+RU: derivation + explicit cost_pricing-stays-distinct decision 7. ✓ test_unrecognised_id_returns_none: glm-4.6/mystery-9/''/None → None
