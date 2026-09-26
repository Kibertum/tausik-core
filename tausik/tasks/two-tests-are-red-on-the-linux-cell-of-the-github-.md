---
slug: two-tests-are-red-on-the-linux-cell-of-the-github-
title: "Two tests are red on the Linux cell of the GitHub matrix: a path spelling only Windows equates, and a wall-clock threshold WSL cannot meet"
status: done
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_config_trust.py"
  - "tests/test_graph_refresh_on_write.py"
  - "tests/test_ci_lanes_are_honest.py"
  - "tests/test_crosscutting_registry.py"
scope_paths:
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-13T18:30:24Z"
resolution: null
resolution_reason: null
---

## Goal

The GitHub workflow runs the fast lane on ubuntu/macos/windows; reproduced in WSL Ubuntu 24.04 / Python 3.12 by the workflow's own steps on HEAD 718f6478: 10303 passed, 2 failed. (1) tests/test_config_trust.py::TestProjectScopedEntries::test_entry_applies_to_its_project_however_the_path_is_spelled uppercases the whole project path — an equivalence only a case-insensitive filesystem grants; on Linux /HOME/X is another directory and the entry rightly does not apply. (2) tests/test_graph_refresh_on_write.py::TestTheCostIsNamedAndGuarded::test_one_refresh_stays_in_single_digit_milliseconds asserts 10 ms of wall clock; on WSL a refresh costs 44.7 ms because SQLite fsync on that disk costs tens of ms — the environment's floor, not a regression. Both tests must say something true on every cell of the matrix.

## Acceptance Criteria

AC-1: the config-trust test derives the 'other spelling' from what os.path.normcase equates on the running platform (separators and a trailing slash everywhere; letter case only where normcase folds it) and passes on Windows and Linux; (negative) on a case-sensitive platform the test asserts the uppercased path is NOT the same project — the entry does not apply. AC-2: the graph-refresh timing test calibrates the environment's floor (one SQLite commit in the same tmp dir) and holds the refresh to max(10 ms, 20 × floor), naming both numbers in the message; a genuine tenfold regression is still caught (negative: a mocked slow refresh exceeds the bar). AC-3: both tests green in WSL by the workflow's steps and on Windows. AC-4 (found by the built snapshot's own lane, 7 failed): the dormancy mark of tests/test_ci_lanes_are_honest.py was overwritten by a second pytestmark assignment 15 lines later — one list now; tests/test_crosscutting_registry.py treats a declared prefix the snapshot leaves behind as dormant, not rot, and a test whose whole scope stayed behind as dormant, not invisible; (negative) on the snapshot those tests SKIP with the dormancy reason and the rest pass; the built snapshot's full lane is green. AC-5: verify signed.

## Plan

## Rollback

## Journal

- 2026-09-13T18:30:20Z [implementation] — Measured BEFORE: WSL Ubuntu 24.04 / Python 3.12, the workflow's own steps on HEAD 718f6478 (clone, pip install pytest pytest-xdist ruff mypy bandit + requirements, bootstrap --no-detect --ide all, gen_doc_constants --check --skip-test-count OK, ruff clean, pytest tests/): 10303 passed, 2 failed — test_config_trust (KeyError task_done: uppercased path is another directory on Linux) and test_graph_refresh_on_write (44.7 ms vs 10 ms: the disk's fsync). Built snapshot c3863918 (tree ea7af472 == filtered HEAD, verify OK) full lane: 7 failed — the dormancy pytestmark of test_ci_lanes_are_honest.py overwritten by a second assignment, and the registry test calling excluded prefixes rot / an excluded-scope test invisible. AC-1 ✓ tests/test_config_trust.py::TestProjectScopedEntries::test_entry_applies_to_its_project_however_the_path_is_spelled derives the spelling from normcase (separators + trailing slash; case only where folded); (NEGATIVE) ::test_on_a_case_sensitive_platform_another_case_is_another_project — skipped on Windows, passes on Linux (entry does not apply). AC-2 ✓ tests/test_graph_refresh_on_write.py::TestTheCostIsNamedAndGuarded::test_one_refresh_stays_in_single_digit_milliseconds calibrates _commit_floor_ms and holds to max(10, 20×floor) naming both; (NEGATIVE) ::test_a_tenfold_regression_is_still_caught. AC-3 ✓ WSL: 103 passed in the two files; Windows: 109 passed, 1 skipped. AC-4 ✓ tests/test_ci_lanes_are_honest.py pytestmark is one list (slow + dormancy); tests/test_crosscutting_registry.py _dormant_here via publication_snapshot.is_excluded; on the snapshot worktree the four files give 7 passed / 26 skipped with the dormancy reason; the built snapshot's full lane: 10452 passed, 198 skipped, 0 failed (was 7 failed). AC-5 ✓ verify run #2639 signed. Domain: every cell of the matrix and the snapshot say something true, or say why they are silent.
