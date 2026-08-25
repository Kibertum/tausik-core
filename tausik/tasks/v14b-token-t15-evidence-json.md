---
slug: v14b-token-t15-evidence-json
title: "B-token-T1.5: task_done evidence JSON schema with backward-compat"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/service_ac_evidence.py (add evidence_json_to_prose helper); scripts/project_parser.py (--evidence-json flag); scripts/project_cli_task.py (CLI dispatch); scripts/service_task_done.py (mutex check + conversion); harness/claude/mcp/project/handlers.py + harness/cursor/mcp/project/handlers.py (MCP arg passthrough); tests/test_ac_evidence_json.py (new file); CHANGELOG.md + docs note."
scope_exclude: "scripts/service_ac_evidence.py existing parse_evidence_lines / match_evidence_to_ac (unchanged — JSON converts to prose that goes through them); scripts/service_gates.py _verify_ac (already handles ✓ markers — no changes); SQL schema (no migration needed); CLI shape of --evidence prose flag (unchanged)."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T17:33:34Z"
---

## Goal

Add structured JSON evidence support: `--evidence-json '{"ac_evidence":[{"n":1,"status":"pass","evidence":"tests/foo.py:bar"}]}'`. Helper parser in service_ac_evidence.py. Backward compat: prose evidence keeps working. Saves ~500 tokens per task close. Spin-off from v14b-token-tier1-quick-wins T1.5.

## Acceptance Criteria

1. CLI: `tausik task done <slug> --ac-verified --evidence-json '{"ac_evidence":[{"n":1,"status":"pass","evidence":"tests/foo.py::test_bar"}]}'` accepted; JSON parsed → canonical prose ("AC verified:\n1. ✓ tests/foo.py::test_bar\n...") → routed through existing task_log path; downstream verification identical to prose --evidence.

2. Schema: top-level `ac_evidence` array; each item requires `n` (int ≥1) + `status` ('pass'|'fail') + `evidence` (str). Optional `manual` (bool) and `negative` (bool) flags emit "manual" / "negative" markers in prose so service_ac_evidence parser flags them correctly.

3. NEGATIVE: malformed JSON (parse error) → ServiceError "invalid --evidence-json: <reason>"; no task_log written (no partial side-effect). Tested.

4. NEGATIVE: missing `ac_evidence` key, `ac_evidence` not a list, item missing `n`/`status`/`evidence`, `n` non-int, `status` not in {pass,fail} → ServiceError with clear field-level reason. Each negative case has a test.

5. NEGATIVE: passing both `--evidence` and `--evidence-json` → ServiceError "mutually exclusive". argparse-level reject preferred (one error message, no partial state).

6. Backward compat: existing `--evidence` (prose) flow unchanged. Regression test asserts a representative prose evidence still produces identical AcCoverageReport.

7. Round-trip: feeding the helper's prose output into service_ac_evidence.build_report() yields covered==total_ac for a 3-item all-pass JSON; gaps non-empty for a mixed pass/fail JSON. Test.

8. New helper `evidence_json_to_prose(raw: str) -> str` in scripts/service_ac_evidence.py — public, raises ServiceError on bad input. Pure function, no DB/IO.

9. MCP tool `tausik_task_done` accepts new `evidence_json` arg; both Claude + Cursor handlers route it through the same conversion. Mutually exclusive with `evidence`. Backward compat: existing `evidence` arg works unchanged.

10. New tests in tests/test_ac_evidence_json.py — ≥10 cases (5 positive: minimal, 3-AC pass, mixed pass/fail, with manual flag, with negative flag; 5 negative: malformed JSON, missing key, item missing n, status invalid, both flags). All PASS.

11. tausik verify --task v14b-token-t15-evidence-json PASS; full pytest suite green (no regressions).

12. Docs: CHANGELOG entry under v1.4 polish; references/agent-contract.md (or docs/ru/agent-contract.md) one-paragraph note + minimal example. No bigger doc rewrite.

13. SECURITY: --evidence-json content is agent-controlled but flows only through json.loads (built-in, no eval) and is converted to prose before hitting any DB write. Test that JSON containing SQL-flavored payload (e.g. evidence="x'); DROP TABLE tasks;--") writes the literal string into notes via task_log without side effects (uses parameterised insert).

## Plan

## Rollback

## Journal

- 2026-05-06T17:20:34Z [implementation] — Plan: thin JSON→prose converter in service_ac_evidence.evidence_json_to_prose; CLI flag + mutex with --evidence; CLI handler routes via service_task_done; MCP handlers (claude+cursor) get evidence_json arg. Existing parse pipeline (parse_evidence_lines, match_evidence_to_ac, _verify_ac) untouched. 10+ tests in tests/test_ac_evidence_json.py.
- 2026-05-06T17:33:18Z [implementation] — AC verified: 1. ✓ tests/test_ac_evidence_json.py::test_minimal_single_ac_pass + manual argparse smoke 2. ✓ test_manual_flag_emits_marker + test_negative_flag_emits_marker 3. ✓ test_malformed_json_raises 4. ✓ test_top_level_not_object/missing_ac_evidence/empty_list/missing_n/n_zero/n_bool/status_invalid/evidence_missing/blank/item_not_object — 10 negative cases 5. ✓ negative: argparse mutex via add_mutually_exclusive_group + service-layer test_service_layer_mutex_prose_and_json 6. ✓ existing test_ac_evidence.py + test_qg2_gates.py + test_senar.py 161 passed unchanged 7. ✓ test_three_ac_all_pass_round_trip + test_mixed_pass_fail_leaves_gap 8. ✓ scripts/service_ac_evidence.py evidence_json_to_prose() — pure function, no IO 9. ✓ harness/{claude,cursor}/mcp/project/tools.py schema + handlers.py passthrough; mirror regenerated via bootstrap 10. ✓ tests/test_ac_evidence_json.py — 19 cases all PASS 11. ✓ tausik verify --task PASS (verify run cached); full pytest 2866 passed 7 skipped 12. ✓ CHANGELOG.md + CHANGELOG.ru.md + docs/ru/agent-contract.md updated 13. ✓ negative: test_sql_payload_is_inert_in_prose — payload survives helper as opaque string; downstream task_log uses parameterised insert
- 2026-05-06T17:33:34Z [implementation] — AC verified: 1. ✓ tests/test_ac_evidence_json.py::test_minimal_single_ac_pass + manual argparse smoke 2. ✓ test_manual_flag_emits_marker + test_negative_flag_emits_marker 3. ✓ test_malformed_json_raises 4. ✓ test_top_level_not_object/missing_ac_evidence/empty_list/missing_n/n_zero/n_bool/status_invalid/evidence_missing/blank/item_not_object — 10 negative cases 5. ✓ negative: argparse mutex via add_mutually_exclusive_group + service-layer test_service_layer_mutex_prose_and_json 6. ✓ existing test_ac_evidence.py + test_qg2_gates.py + test_senar.py 161 passed unchanged 7. ✓ test_three_ac_all_pass_round_trip + test_mixed_pass_fail_leaves_gap 8. ✓ scripts/service_ac_evidence.py evidence_json_to_prose() pure function no IO 9. ✓ harness claude+cursor mcp project tools.py schema + handlers.py passthrough; mirror regenerated via bootstrap 10. ✓ tests/test_ac_evidence_json.py — 19 cases all PASS 11. ✓ tausik verify --task PASS exit=0; full pytest 2866 passed 7 skipped 12. ✓ CHANGELOG.md + CHANGELOG.ru.md + docs/ru/agent-contract.md updated 13. ✓ negative: test_sql_payload_is_inert_in_prose payload survives helper as opaque string; downstream task_log uses parameterised insert
