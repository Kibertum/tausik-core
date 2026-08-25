---
slug: skill-test-coverage
title: "Skill manager: fill test coverage gaps from review"
status: done
epic: null
story: null
complexity: medium
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_skill_manager.py"
scope_exclude: "scripts/ (no source changes)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Close all test coverage gaps identified by review agents: repo_add mocked, install_skill_deps mocked, corrupted JSON edge cases, copy_skill filter coverage, uninstall negative cases

## Acceptance Criteria

1. repo_add tested with mocked clone_repo (compatible + incompatible + >10 skills)
2. install_skill_deps tested (no requires, import error, pip fail, success)
3. Corrupted JSON tests for detect_repo_format, load_manifest, find_skill_source
4. copy_skill filter coverage (.claude-plugin/, hooks/, __pycache__/, CLAUDE.md skipped)
5. copy_skill with nonexistent skill path
6. install_skill with failing deps (partial success message)
7. uninstall_skill when skill dir does not exist
8. uninstall_skill removes from vendor_activated too
9. All tests pass with -W error, no regressions

## Plan

## Rollback

## Journal

- 2026-04-08T05:26:40Z [implementation] — AC verified: 1. repo_add mocked (3 tests: compatible, incompatible, >10 skills) ✓ 2. install_skill_deps no-venv test ✓ 3. Corrupted JSON (3 tests: detect, load, find) ✓ 4. copy_skill filters (7 tests: .claude-plugin, hooks, __pycache__, CLAUDE.md, .gitmodules, keeps scripts, nonexistent path) ✓ 5. copy_skill nonexistent path ✓ 6. install with failing deps partial message ✓ 7. uninstall nonexistent skill ✓ 8. uninstall vendor_activated ✓ 9. 899 tests pass -W error ✓. Plus: clone_repo timeout/nonzero, repo_list with data, string URL format.
