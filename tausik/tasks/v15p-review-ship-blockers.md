---
slug: v15p-review-ship-blockers
title: "[P0] Fix v1.5 review ship-blockers: scope_paths='[]', version-op, CHANGELOG/cli.md gaps"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_qg0_check.py, scripts/project_cli_aidd_validate.py, scripts/service_task.py (task_delete meta cleanup), scripts/service_delegate.py (handoff raise), scripts/project_cli_aidd_autogen.py (sanitize + lang budget), CHANGELOG.md + .ru.md, docs/{en,ru}/cli.md, tests/*"
scope_exclude: "the 24 LOW findings (observability/test-gaps) — separate follow-up; no behavior change beyond the listed fixes"
relevant_files:
  - "scripts/gate_qg0_check.py"
  - "scripts/project_cli_aidd_validate.py"
  - "scripts/service_task.py"
  - "scripts/service_delegate.py"
  - "scripts/project_cli_aidd_autogen.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - "docs/_generated/constants.json"
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T21:53:12Z"
---

## Goal

Fix the confirmed ship-blocking findings from the v1.5 swarm review: (HIGH-1) scope_paths='[]' passes QG-0 but the write-gate blocks all edits — treat a parsed-empty scope_paths as 'no declaration' in QG-0 so it can't pass falsely; (HIGH-2) aidd validate _minor_version ignores the requires-python operator → false drift; (DOC-3) orchestrator-worker epic missing from CHANGELOG [Unreleased] EN+RU; (DOC-11) renar export + the new aidd/task-delegation commands missing from docs/{en,ru}/cli.md. Plus cheap correctness MEDIUMs: task_delete must clear delegation/worker_summary meta; task_handoff must raise on a non-delegated task; autogen must sanitize repo signals injected into markdown; _detect_languages budget should count only code files.

## Acceptance Criteria

AC1: a parsed-empty scope_paths ('[]') no longer satisfies QG-0 scope declaration (it's treated like no scope) — so a medium/complex task can't pass QG-0 yet be write-blocked. AC2: aidd validate _verify_lang_version is operator-aware: '>='/'~=' → ok when claim_ver>=req floor (same major); '=='/bare → exact match; the dominant pin-vs-floor case no longer false-drifts. AC3: CHANGELOG.md + CHANGELOG.ru.md [Unreleased] gain an orchestrator-worker section. AC4: docs/{en,ru}/cli.md document `renar export`, the `aidd autogen/validate`, and `task delegate/undelegate/handoff/summary-back` commands. AC5: task_delete clears delegation:<slug> + worker_summary:<slug> meta; task_handoff raises ServiceError on a non-delegated task; autogen sanitizes \n/\r in injected repo signals; _detect_languages counts only code files toward its budget. AC6: tests cover each fix; ruff+mypy clean; filesize<400; gen_doc_constants green. Negative: scope_paths='[]' on a medium task is REJECTED at QG-0 with the scope message (not a pass-then-block); a non-delegated task_handoff raises (not a silent empty contract).

## Plan

## Rollback

git revert; each fix is small + localized; no schema migration.

## Journal

- 2026-06-14T21:51:35Z [implementation] — Fixed v1.5 swarm-review ship-blockers. HIGH-1: gate_qg0_check._has_scope_paths — parsed-empty '[]' no longer satisfies QG-0 scope decl (was pass-then-write-block). HIGH-2: aidd validate _verify_lang_version operator-aware — req floor (>=/~=/>) + exact claim pin → ok when pin>=floor (same major); both-floors must agree; exact req → exact match. Fixed pre-existing nuance (floor-vs-floor mismatch stays drift). DOC: CHANGELOG [Unreleased] EN+RU gained orchestrator-worker section; cli.md EN+RU gained renar export + task delegate/undelegate/handoff/summary-back. MEDIUM: task_delete clears delegation+worker_summary meta; task_handoff raises on non-delegated; autogen _fmt _sanitize (\n/\r → no md-injection); _detect_languages counts only code files toward budget. ~12 tests added/updated; 191+ green; full ruff+mypy clean (210); constants 4322.
- 2026-06-14T21:52:00Z [implementation] — AC verified: 1. ✓ scope_paths='[]' rejected at QG-0 — test_empty_scope_paths_does_not_pass_qg0 + test_nonempty_scope_paths_passes (gate_qg0_check._has_scope_paths). 2. ✓ aidd validate operator-aware — test_floor_satisfied_by_higher_pin, test_floor_not_satisfied_below, test_exact_spec_requires_exact, test_drift_when_version_mismatch (floor-vs-floor), test_no_false_ok_on_version_prefix_substring. 3. ✓ CHANGELOG.md+.ru.md [Unreleased] orchestrator-worker section added. 4. ✓ docs/{en,ru}/cli.md: renar export + task delegate/undelegate/handoff/summary-back documented. 5. ✓ task_delete clears delegation+worker_summary meta (test_task_delete_clears_delegation_meta); task_handoff raises on non-delegated (test_non_delegated_task_raises); autogen _fmt sanitizes \n/\r (TestFmtSanitizes); _detect_languages counts only code files. 6. ✓ ~12 tests; full ruff+mypy clean (210); filesize<400; gen_doc_constants green (4322). Negative: scope_paths='[]' on medium REJECTED at QG-0 (not pass-then-block); non-delegated handoff raises (not empty contract). Root cause (category: logic-error): is-not-None scope check + operator-blind version compare from the initial v15 build; Prevention: parsed-empty check + operator-aware compare with tests.
