---
slug: renar-qg0-adapt-context-gate
title: "Cross-cutting: ADAPT backward-findings strengthen QG-0 for substantial/deep tiers"
status: done
epic: renar-adoption
story: renar-substrate-and-reach-1
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_qg0_renar.py (new: renar_qg0_advisory free fn), scripts/gate_qg0_check.py (optional renar_advisory_fn param), scripts/service_gates.py (wire callback), docs/{en,ru}/architecture.md (advisory-first ladder), tests/test_renar_qg0_advisory.py"
scope_exclude: "NO hard-gate (rung 3, 2.0); NO QG-2 verifies_version_pin (2.0); NO RENAR-2 signing (2.0); ADAPT backward-findings deep inspection deferred (lite checks presence only)"
relevant_files:
  - "scripts/gate_qg0_renar.py"
  - "scripts/gate_qg0_check.py"
  - "scripts/service_gates.py"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "tests/test_renar_qg0_advisory.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T19:30:13Z"
---

## Goal

RENAR-lite, rung 2 (Decision #115): QG-0 surfaces a NON-blocking advisory when a high-stakes task (tier substantial/deep, or complexity complex as fallback) starts without a linked SPEC and without an ADAPT — nudging the agent to author the interpretation+gap artifact before coding. Advisory only (never raises), config-toggleable (renar.qg0_advisory, default on). Hard-gate promotion and QG-2 version-pin are explicitly DEFERRED to 2.0 (rungs 3-4).

## Acceptance Criteria

AC1: starting a substantial/deep (or complex) task with NO linked SPEC and NO ADAPT appends an advisory warning to QG-0 output (visible at task_start), naming the missing artifact and pointing to spec_link / adapt_create. AC2: a low-stakes task (trivial/light/moderate tier and not complex) gets NO advisory. AC3: a task that already has a linked SPEC (or an ADAPT) gets NO advisory. AC4: the advisory NEVER blocks task_start (it's a warning, not a ServiceError) and is suppressed when config renar.qg0_advisory=false. AC5: tests cover present/absent/toggle-off/non-blocking; ruff+mypy clean; filesize<400. Negative: a backend/config error while computing the advisory must be swallowed (return no advisory), never break task_start.

## Plan

## Rollback

git revert; advisory is additive + config-toggle off (renar.qg0_advisory=false) disables instantly; gate_qg0_check param is optional/back-compatible.

## Journal

- 2026-06-14T19:29:56Z [implementation] — Implemented RENAR-lite rung 2 (Decision #115): gate_qg0_renar.renar_qg0_advisory free fn — non-blocking nudge for high-stakes task (tier substantial/deep or complexity complex) without linked SPEC (specs_for_task) and without ADAPT (adapts_for_target task). Fully defensive (config/backend error→None). Wired via new optional renar_advisory_fn param in check_qg0_start, lambda in service_gates._check_qg0_start. config toggle renar.qg0_advisory default on. Docs: advisory-first ladder table in architecture.md EN+RU. 9 tests (present/complex-fallback/low-stakes/spec-suppress/adapt-suppress/backend-error/toggle-off + non-blocking integration ×2). Hard-gate + version-pin + RENAR-2 explicitly deferred to 2.0.
- 2026-06-14T19:30:13Z [implementation] — AC1: ✓ high-stakes (deep/complex) task w/o SPEC+ADAPT → advisory appended naming missing artifact + spec_link/adapt_create hint (test_high_stakes_without_artifacts_nudges, test_complex_fallback). AC2: ✓ low-stakes (light/simple) → no advisory (test_low_stakes_no_advisory). AC3: ✓ linked SPEC or existing ADAPT suppresses (test_linked_spec_suppresses, test_existing_adapt_suppresses). AC4: ✓ never blocks — appended as warning via check_qg0_start, suppressed when renar.qg0_advisory=false (test_advisory_appended_not_raised, test_toggle_off_suppresses); callback error swallowed (test_advisory_callback_error_is_swallowed). AC5: ✓ 9 tests; ruff+mypy clean (208 files); gate_qg0_renar 60, gate_qg0_check 235, service_gates 397 (<400). Domain: a real deep task without a requirement artifact now gets a visible, non-blocking RENAR nudge at task_start — interpretation made visible without ceremony. Negative: backend/config error → returns None (test_backend_error_swallowed), QG-0 never broken.
