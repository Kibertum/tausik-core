---
slug: v155-provider-tests
title: "Tests: providers + routing kilo/GLM cases"
status: done
epic: v155-kilo-zai
story: v155-provider-abstraction
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "tests/test_providers.py (new), tests/test_model_profiles.py (new), tests/test_model_routing.py, tests/test_task_start_model_banner.py"
scope_exclude: "scripts/* (done), bootstrap/*, docs/*"
relevant_files:
  - "tests/test_providers.py"
  - "tests/test_model_profiles.py"
  - "tests/test_model_routing.py"
  - "tests/test_task_start_model_banner.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T08:24:12Z"
---

## Goal

Add tests/test_providers.py (registry, base contract, claude/cursor/kilo/qwen entries, no zai) and extend test_model_routing for GLM family + flagship-tier resolution + provider-aware detection. All green via tausik verify.

## Acceptance Criteria

1. New tests/test_providers.py: registry available()==[claude,cursor,kilo,qwen]; base contract (each provider has name/get_active_model/get_transcript_path); claude delegates to model_routing parser; kilo reads KILO_MODEL env and .kilocode config; reset() re-registers; malformed module skipped. 2. New tests/test_model_profiles.py: load_families merge+defaults, vendor_of, rank_of (highest-rank wins), spec_for fallback, default_family. 3. Extend tests/test_model_routing.py with GLM family cases: suggest_model(family='glm') resolves GLM ids; family=None stays claude. 4. Banner test (in test_task_start_model_banner or new): glm active → GLM recommendation + same-id match; default_family fallback; glm-4.5-air complex → mismatch. 5. All green via pytest; ruff+mypy clean on test files. NEGATIVE: test that providers.get('zai') raises KeyError; load_families(non-dict) returns defaults; suggest_model(family='nonexistent') falls back to claude; vendor_of(None) is None.

## Plan

## Rollback

git checkout tests/test_model_routing.py tests/test_task_start_model_banner.py && rm tests/test_providers.py tests/test_model_profiles.py — test-only additions, no runtime impact.

## Journal

- 2026-06-19T08:23:59Z [implementation] — Added tests/test_providers.py (10 tests: registry, base contract, claude delegation, kilo env/config, reset re-register, malformed-module skip, zai KeyError) + tests/test_model_profiles.py (8 tests: defaults, merge/extend, malformed-skip, vendor_of, rank_of highest-wins, spec_for fallback, default_family). Extended test_model_routing.py (+6 GLM family/tier cases) and test_task_start_model_banner.py (+TestBannerGlmFamily 4 cases: glm match, default_family fallback, underpowered mismatch, claude unchanged). 98 pass, ruff clean.
- 2026-06-19T08:24:12Z [implementation] — AC1 ✓ tests/test_providers.py (registry, base contract, claude delegation, kilo env+config, reset, malformed-skip). AC2 ✓ tests/test_model_profiles.py (load_families merge/defaults/malformed, vendor_of, rank_of highest-wins, spec_for fallback, default_family). AC3 ✓ test_model_routing.py GLM cases: tests/test_model_routing.py::test_glm_family_resolves_glm_ids, ::test_family_none_defaults_to_claude. AC4 ✓ test_task_start_model_banner.py::TestBannerGlmFamily (glm match, default_family, underpowered mismatch, claude unchanged). AC5 ✓ 98 passed, ruff clean. NEGATIVE ✓ test_zai_is_not_a_provider (KeyError), test_load_families_non_dict_returns_defaults, test_nonexistent_family_falls_back_to_claude, vendor_of(None) in test_vendor_of. Domain: tests assert the real z.ai/GLM user workflow end-to-end (detect glm-* → route GLM → correct verdict).
