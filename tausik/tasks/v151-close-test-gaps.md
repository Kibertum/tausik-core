---
slug: v151-close-test-gaps
title: "[P2] Close v1.5 review test-gaps (deferred from memory #172)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/ only (test_ow_delegate.py, test_renar_qg0_advisory.py, test_aidd_validate.py, test_aidd_autogen.py) — adding coverage, no src changes expected"
scope_exclude: "no src behavior changes (pure test additions); if a test reveals a real bug, fix minimally"
relevant_files:
  - "tests/test_v15_test_gaps.py"
  - "tests/test_gen_doc_constants.py"
  - "scripts/doc_drift_scanners.py"
  - "docs/_generated/constants.json"
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T23:39:17Z"
---

## Goal

Close the deferred test-gaps the swarm review flagged (memory #172) so the v1.5 features are guarded against regression: task_delegation() with non-dict-but-valid JSON returns None; delegate on a blocked task + delegate→done coherence; RENAR advisory with blank/missing task fields; aidd validate drift exit-1 path; aidd autogen leading-'##' template handling; aidd init missing-template path. Add the meaningful ones; skip any that prove redundant with existing coverage.

## Acceptance Criteria

AC1: task_delegation() returns None for a stored non-dict JSON value (e.g. '"x"' or '[1]'). AC2: delegate works after a status change (blocked task can be delegated) and a delegated task that reaches done is coherent. AC3: renar_qg0_advisory handles a task dict missing tier/complexity (no crash, no advisory). AC4: aidd validate returns exit-relevant drift for a non-filesize claim too (lang/lint/test). AC5: aidd autogen render_vision handles a template whose first line is '## ' (leading section, no preceding '# '). AC6: all new tests pass; ruff+mypy clean. Negative: each test asserts the safe/None/no-crash path for the malformed/edge input.

## Plan

## Rollback

git revert; tests-only.

## Journal

- 2026-06-14T23:38:44Z [implementation] — Added 6 regression tests (test_v15_test_gaps.py) for the #172 gaps: task_delegation non-dict/list JSON→None, delegate-after-blocked, renar advisory bare-task→None, aidd validate lint-drift exit-1, render_vision leading-'##' template. All passed first try — behaviors were already correct, just untested. Bonus: the gen_doc_constants --check went RED on close (CLAUDE.md memory-tail surfaced memory #86 'v1.4' after I added #172) — fixed the scanner (doc_drift_scanners._strip_dynamic_block: exclude CLAUDE.md DYNAMIC block from version-ref scan, since the auto-generated memory-tail cites historical version titles legitimately; same class as decision #105 foreign-version). +2 scanner tests (dynamic-block ignored, static-body still flagged). full mypy/ruff clean (210), constants green.
- 2026-06-14T23:39:09Z [implementation] — AC verified: 1. ✓ task_delegation non-dict/list JSON → None (test_non_dict_json_returns_none, test_list_json_returns_none). 2. ✓ delegate-after-blocked works (test_delegate_after_blocked). 3. ✓ renar advisory bare task dict → None no crash (test_bare_task_dict_no_crash_no_advisory). 4. ✓ aidd validate lint-tool drift → exit 1 (test_lint_tool_drift_exits_1). 5. ✓ render_vision leading-'##' template no crash + facts present (test_template_starting_with_section_heading). 6. ✓ all pass; ruff+full mypy clean (210); + scanner fix (CLAUDE.md DYNAMIC block excluded from version-ref scan) with 2 guard tests. Negative: each asserts the None/no-crash/safe path for malformed/edge input; scanner static-body drift still flagged (test_scan_version_refs_flags_static_body_drift_in_claudemd).
