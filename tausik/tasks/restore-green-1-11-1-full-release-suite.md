---
slug: restore-green-1-11-1-full-release-suite
title: "Restore green 1.11.1 full release suite"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "tausik/gates.json ruff-format legacy entries, stale memory reference artifacts, managed DB backup retention, ship skill route wording and generated profiles, ROADMAP version-policy projection, and directly aligned tests."
scope_exclude: "No ratchet increases, test skips, live database deletion, feature work, or public release action before gates are green."
relevant_files:
  - "tausik/gates.json"
  - "harness/skills/ship/SKILL.md"
  - ROADMAP.md
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_gate_ruff_format.py"
  - "tests/test_repo_hygiene_ratchet.py"
  - "tests/test_subagent_model_hints.py"
  - "tests/test_release_roadmap.py"
  - "tests/test_roadmap_follows_the_close.py"
  - "tausik/memory/close-qg-2-with-full-prose-ac-evidence-whose-tests-were.md"
  - "tausik/memory/run-a-combined-bootstrap-regression-slice-including-tests.md"
  - "tausik/memory/run-a-guessed-set-of-migration-and-cli-test-filenames-in.md"
  - "tausik/memory/run-scoped-suite-with-tests-test-bootstrap-drift-py.md"
  - "tausik/memory/run-the-combined-bootstrap-host-test-set-with-tests-test.md"
  - "tausik/memory/run-the-documentation-slice-with-tests-test-docs-py.md"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:33:40Z"
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

Resolve the four deterministic full-suite failures found during the 1.11.1 release gate without weakening their ratchets.

## Acceptance Criteria

AC-1 ruff-format legacy list contains only genuinely unformatted files. AC-2 stale-memory-ref ratchet is restored by repairing or intentionally accounting for every reported reference. AC-3 managed DB backups comply with keep<=3 without deleting the live database. AC-4 ship skill exposes the required code-review subagent route contract. AC-5 the four focused tests and canonical full suite pass with denominators. Negative: do not raise ratchets, skip tests, use --no-verify, or delete the live TAUSIK database.

## Plan

## Rollback

Revert the focused repairs; retain the release block and original ratchets until a replacement fix passes the same full suite.

## Journal

- 2026-10-04T12:31:14Z [implementation] — Verification: focused release-gate regression set passed 51 tests; canonical full suite collected 12,958 items and finished 12,921 passed, 37 skipped, 0 deselected, 0 failed, 62 warnings in 459.32s; audit_pytest_dedupe passed with 282 parallel groups, 669 tests, 0 copy groups, and no fake-test findings among 7,829 functions.
- 2026-10-04T12:33:22Z [implementation] — AC-1 PASS: ruff legacy ratchet focused tests passed and the four formatted paths were removed without raising the baseline. AC-2 PASS: stale-memory reference gate passed after repairing six historical projections. AC-3 PASS: managed-backup retention gate passed with the live database preserved. AC-4 PASS: ship skill and generated profiles expose the required code-review route and model hints. AC-5 PASS: 51 focused tests passed; verify #3477 passed 678 tests with 19 deselected and 8/9 gates executed; canonical full suite collected 12,958 items and finished 12,921 passed, 37 skipped, 0 deselected, 0 failed. Negative PASS: no ratchet increase, test skip, --no-verify bypass, or live database deletion was used.
- 2026-10-04T12:33:31Z [implementation] — Root cause (regression): release changes outgrew four repository ratchets: formatted paths remained in the legacy list, historical memory projections retained nonexistent file tokens, the ship contract omitted the canonical route marker, and ROADMAP still projected the old version policy. Prevention: keep ratchets shrinking with source changes, regenerate managed profiles and roadmap after contract decisions, and run the unfiltered release suite before release closure.
- 2026-10-04T12:33:39Z [implementation] — AC-1 PASS: ruff legacy ratchet focused tests passed and the four formatted paths were removed without raising the baseline. AC-2 PASS: stale-memory reference gate passed after repairing six historical projections. AC-3 PASS: managed-backup retention gate passed with the live database preserved. AC-4 PASS: ship skill and generated profiles expose the required code-review route and model hints. AC-5 PASS: 51 focused tests passed; verify #3477 passed 678 tests with 19 deselected and 8/9 gates executed; canonical full suite collected 12,958 items and finished 12,921 passed, 37 skipped, 0 deselected, 0 failed. Negative PASS: no ratchet increase, test skip, --no-verify bypass, or live database deletion was used.
- 2026-10-04T12:33:46Z [done] — Closure evidence: ✓ AC-1 legacy ruff baseline shrank and focused gate passed. ✓ AC-2 stale memory references were repaired and gate passed. ✓ AC-3 backup retention passed while live DB remained intact. ✓ AC-4 ship route contract passed source and generated-profile tests. ✓ AC-5 focused 51, scoped 678, and full 12,921-test lanes passed with denominators. ✓ Negative constraint: no ratchet widening, skips, bypass, or live DB deletion. Domain: generated skills, roadmap, memory projections, gate baselines, and database backup inventory are semantically consistent in the deployed repository, not only accepted by mocks.
