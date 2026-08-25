---
slug: v14b-service-gates-debt-paydown
title: "v1.4-tail filesize debt #5/5: split scripts/service_gates.py 653→<400"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/service_gates.py (modify); scripts/gate_qg0_check.py (NEW); scripts/gate_ac_check.py (NEW); CHANGELOG.md + CHANGELOG.ru.md (entry under Unreleased v1.4.0 polish Phase B); .tausik/config.json gates.filesize.exempt_files (remove service_gates.py if listed)"
scope_exclude: "scripts/service_verification.py (consumer, not split target); scripts/gate_negative_scenario.py + scripts/gate_qg0_score.py (already extracted in prior splits, leave alone); scripts/service_ac_evidence.py (consumer); .claude/ tree (regenerated from bootstrap; never edit directly); test files (only adjust imports if break)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T20:22:07Z"
---

## Goal

Last filesize-debt candidate after tools_extra/project_backend/bootstrap_copy/brain_init splits this thread. scripts/service_gates.py = 653 lines (253 over 400 limit). Split by responsibility (Pattern #91): extract QG-0 Context Gate (check_qg0_start + SECURITY_KEYWORDS) into gate_qg0_check.py, extract QG-2 AC/Plan/Checklist verification (4 pure functions) into gate_ac_check.py. Verify-pipeline + Verify-First Contract methods stay in service_gates.py as they depend on self.be._conn/self.be.task_append_notes. After split: service_gates.py ~370, two new files <250 each. Re-export constants and renamed-public functions for backward compatibility (preserve `from service_gates import SECURITY_KEYWORDS` etc.). Once landed, the v1.4-tail filesize-gate exempt_files list is structurally clean — no further splits needed.

## Acceptance Criteria

1. scripts/service_gates.py reduced to <400 lines (filesize gate green without exemption).
2. Two new modules created: scripts/gate_qg0_check.py (<250 lines) with check_qg0_start + SECURITY_KEYWORDS + SECURITY_AC_KEYWORDS; scripts/gate_ac_check.py (<250 lines) with verify_ac, verify_plan_complete, check_verification_checklist, determine_checklist_tier as pure free functions.
3. Backward compatibility preserved: `from service_gates import SECURITY_KEYWORDS, SECURITY_AC_KEYWORDS` still works (re-exported with `# noqa: F401`).
4. GatesMixin public method names unchanged (_check_qg0_start, _verify_ac, _verify_plan_complete, _check_verification_checklist, _determine_checklist_tier, run_verify_for_task, _run_quality_gates_report, _enforce_verify_first, _run_quality_gates, _extract_files_from_gate_output).
5. Negative: no test imports break — full pytest suite green; ruff + mypy clean; bootstrap re-run produces zero .claude/ diffs (skip if no .claude regen needed).
6. Negative: no behavior regression — gate_runner integration tests still pass; QG-0 still rejects task_start without goal/AC/negative-scenario; QG-2 still rejects close without verify-first cache hit (when verify gates configured).

## Plan

[{"step": "Read existing similar splits (gate_negative_scenario.py, gate_qg0_score.py) for style/import pattern", "done": true}, {"step": "Check tests/test_service_gates*.py + tests/test_gate_*.py for current import patterns and what to preserve", "done": true}, {"step": "Check .tausik/config.json for filesize exempt_files entry on service_gates", "done": true}, {"step": "Create scripts/gate_qg0_check.py: SECURITY_KEYWORDS + SECURITY_AC_KEYWORDS + check_qg0_start free function", "done": true}, {"step": "Create scripts/gate_ac_check.py: verify_ac + verify_plan_complete + check_verification_checklist + determine_checklist_tier free functions", "done": true}, {"step": "Modify scripts/service_gates.py: re-exports (security keywords) + GatesMixin methods as 2-3 line delegators", "done": true}, {"step": "Run pytest -x on gate-related tests (test_service_gates, test_gate_*, test_audit_*)", "done": true}, {"step": "Run ruff + mypy on changed files", "done": true}, {"step": "Verify filesize gate green via .tausik/tausik verify --task v14b-service-gates-debt-paydown", "done": true}, {"step": "Remove service_gates.py from .tausik/config.json gates.filesize.exempt_files if present", "done": true}, {"step": "Bootstrap copy step (if needed): python .tausik-lib/bootstrap/bootstrap.py --init then verify zero .claude/ diff", "done": true}, {"step": "Add CHANGELOG entries (EN + RU) under Unreleased v1.4.0 polish Phase B", "done": true}]

## Rollback

## Journal

- 2026-05-06T20:14:54Z [implementation] — Split landed: service_gates.py 653→368 (-285); gate_qg0_check.py 171 NEW (SECURITY_KEYWORDS+SECURITY_AC_KEYWORDS+check_qg0_start); gate_ac_check.py 223 NEW (verify_ac+verify_plan_complete+determine_checklist_tier+check_verification_checklist as pure functions). All under 400/250 limits. Re-exports: SECURITY_KEYWORDS, SECURITY_AC_KEYWORDS, has_negative_scenario, NEGATIVE_SCENARIO_KEYWORDS, qg0_dimensions_score, check_qg0_start. Mixin methods now delegate. Pytest full suite: 2889 passed / 7 skipped / 120 deselected. ruff + mypy clean on 3 files.
- 2026-05-06T20:22:04Z [implementation] — AC verified: 1. ✓ scripts/service_gates.py = 368 lines (<400, filesize gate PASS no exemption). 2. ✓ scripts/gate_qg0_check.py = 171 lines (<250) with check_qg0_start + SECURITY_KEYWORDS + SECURITY_AC_KEYWORDS; scripts/gate_ac_check.py = 223 lines (<250) with verify_ac, verify_plan_complete, check_verification_checklist, determine_checklist_tier as pure free functions. 3. ✓ Backward compat: from service_gates import SECURITY_KEYWORDS, SECURITY_AC_KEYWORDS, has_negative_scenario, NEGATIVE_SCENARIO_KEYWORDS, qg0_dimensions_score, check_qg0_start all re-exported via # noqa: F401. 4. ✓ GatesMixin public method names unchanged: _check_qg0_start, _verify_ac, _verify_plan_complete, _check_verification_checklist, _determine_checklist_tier, run_verify_for_task, _run_quality_gates_report, _enforce_verify_first, _run_quality_gates, _extract_files_from_gate_output — all delegate to free functions. 5. ✓ Negative: full pytest 2889 passed / 7 skipped / 120 deselected; ruff + mypy clean on 3 files; .claude/scripts/{service_gates,gate_qg0_check,gate_ac_check}.py identical to root (zero bootstrap diff). 6. ✓ Negative: no behavior regression — gate-related tests (244) focused-pass; QG-0 still rejects task_start without goal/AC/negative-scenario (verified empirically when this task itself was created); QG-2 still rejects close without verify-first cache hit (just hit cache for verify run #502 before this log).
