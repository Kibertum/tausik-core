---
slug: fix-drift1-delta-crash
title: "drift-1: tolerate non-numeric delta_n instead of crashing the detector"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: light
call_budget: 12
defect_of: null
scope: "scripts/renar_drift.py (delta_n parse in detect_schema_drift), tests/test_renar_drift.py (add case)"
scope_exclude: "renar_conformance.py, gate wiring, CLI parsers, docs (no behavior change there)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T22:24:17Z"
---

## Goal

SENAR Rule 9.5 sweep finding (session #87, tausik-reviewer HIGH). drift-1 schema detector calls int(a['delta_n']) which raises ValueError on a non-numeric corrupt delta_n — the exact malformed-DB state drift-1 exists to surface. Make it emit an 'adapt-delta-invalid' finding instead of crashing (CLI: uncaught traceback; gate: silently swallowed clean). Detector must degrade to a finding, never crash.

## Acceptance Criteria

1. detect_schema_drift emits an 'adapt-delta-invalid' finding (det=drift-1-schema) when delta_n is a non-numeric string, instead of raising. 2. Valid numeric delta_n (int or numeric-string '2') still parses and the existing negative/orphan/base-has-parent checks run unchanged. 3. NEGATIVE: a corrupt adapt row with delta_n='N/A' run through `tausik drift` returns a finding and exits cleanly (no traceback), and the gate path counts it (no silent swallow). 4. New unit test in tests/test_renar_drift.py covers the non-numeric path; full test_renar_drift.py + test_renar_conformance.py green.

## Plan

## Rollback

git revert the single commit; isolated to renar_drift.py delta_n parse + one test — no schema/migration/state change.

## Journal

- 2026-06-13T22:21:27Z [implementation] — Fixed: int(delta_n) wrapped in try/except (ValueError,TypeError) → emits 'adapt-delta-invalid' finding + continue, instead of crashing detector. Added test_adapt_delta_non_numeric (delta_n='N/A' → finding emitted, no orphan double-report, no raise). 26 passed (was 25).
- 2026-06-13T22:24:17Z [implementation] — AC verified (session #87 sweep fix): 1.✓ delta_n non-numeric → 'adapt-delta-invalid' finding emitted (tests/test_renar_drift.py::test_adapt_delta_non_numeric). 2.✓ numeric delta_n unchanged — existing negative/orphan/base-has-parent tests still green. 3.✓ NEGATIVE delta_n='N/A' returns finding, no raise; detector degrades not crashes; signed-corruption NOT masked (test_adapt_delta_invalid_does_not_mask_signature). 4.✓ pytest tests/test_renar_drift.py tests/test_renar_conformance.py = 27 passed; ruff clean. Reviewer round-2: MEDIUM (continue masked signed-check) fixed via delta_n=None + unconditional signature check.
- 2026-06-13T22:24:35Z [done] — Verification-checklist (QG-2, high): scope=renar_drift.py delta_n parse only, no schema/CLI/gate change. tests=tests/test_renar_drift.py::test_adapt_delta_non_numeric + ::test_adapt_delta_invalid_does_not_mask_signature; 27 passed; ruff clean. security=no new surface — read-only detector over live DB, no user input reaches SQL (parameterless literal queries); corrupt delta_n now reported not crashed. edge-cases=None/''→0 (pre-existing or-0 behavior, out of scope), non-numeric string→finding+skip-delta-checks, signed-corruption co-occurrence preserved. Domain: a real corrupt adapt row makes drift-1 emit a finding and exit 0 instead of tracebacking the CLI / silently passing the gate.
