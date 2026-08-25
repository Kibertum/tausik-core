---
slug: firewall-find-exec-delete-uncovered
title: "`find / -delete` и `find / -exec rm -rf {} \\;` не видит ни один детектор — рекурсию несёт find, а не rm"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/hooks/danger_patterns.py (add find detector + wire into wiped_root_any); the existing firewall test file (regression tests both sides). CHANGELOG.md + CHANGELOG.ru.md."
scope_exclude: "scripts/hooks/rm_wipe_detect.py root SET (_WIPE_ROOTS) is REUSED, not modified — whether ~ / bare * / -type-only scoping count stays with firewall-rm-wipe-targets-policy. xargs/`sh -c`-wrapped deletes and non-rm delete verbs deferred (stated as residual). Do NOT touch the rm or PowerShell detectors."
relevant_files:
  - "scripts/hooks/danger_patterns.py"
  - "tests/test_powershell_channel.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T14:45:18Z"
---

## Goal

find / -delete, find . -delete, find / -exec rm -rf {} \;, find / -type f -exec rm -f {} + all pass rc=0. Root cause (confirmed against CURRENT code, not the task's original file guesses): scripts/hooks/danger_patterns.py::_posix_rm_wipes_a_root judges the operands of rm itself; in the -exec form rm's operand is {} and the root is an argument to find, and -delete invokes no rm at all. Both rm_wipe_detect.py:19-21 and danger_patterns.py:131-133 already DOCUMENT this as an uncovered class filed to this task. Fix: add a find-based deleting-detector in danger_patterns.py wired into wiped_root_any, reusing rm_wipe_detect.is_wipe_root/normalise_operand for root-detection so find's and rm's notion of 'root' cannot drift (the anti-drift requirement, conventions #266/#289). NOTE: the task originally named scripts/bash_firewall.py + scripts/rm_wipe_detect.py — those paths are wrong; the real files are scripts/hooks/{bash_firewall,danger_patterns,rm_wipe_detect}.py.

## Acceptance Criteria

1. danger_patterns.py gains a find deleting-detector wired into wiped_root_any, reusing rm_wipe_detect.is_wipe_root + normalise_operand (NO second 'what is root' ruleset). 2. BLOCKS: `find / -delete`, `find . -delete`, `find -delete` (default path .), `find / -exec rm -rf {} \;`, `find / -type f -exec rm -f {} +`, `find / -execdir rm {} +`, `find / -name '*.log' -delete` (hard root blocks even name-scoped), `find .. -delete`. 3. ALLOWS (no over-block): `find . -name '*.pyc' -delete`, `find ./build -delete`, `find src -exec rm {} +`, `find /var/log/app -name '*.log' -exec rm {} +`, `find / -type f -name '*.tmp'` (no delete action), `find . -type d` (no delete). 4. Root-detection is is_wipe_root/normalise_operand verbatim — find and rm agree on every root spelling. 5. Regression tests BOTH sides added to the existing firewall test file; scoped + full suite green, 0 warnings. 6. Residual coverage boundary STATED (not silent): xargs/`sh -c` wrapped deletes and non-rm exec verbs beyond rm/rmdir/unlink/shred are NOT covered. NEGATIVE/BOUNDARY: 7. `find . -name '*.pyc' -delete` and `find ./subdir -delete` are NOT blocked (cwd delete blocks only when NOT name/path-scoped; a named subdir is never a wipe root); a non-deleting find is never blocked.

## Plan

## Rollback

git revert — the change is a purely additive find detector + its wiring in wiped_root_any; no existing detector or root definition is modified.

## Journal

- 2026-07-26T14:44:32Z [implementation] — AC verified: 1. ✓ danger_patterns.py: _posix_find_wipes_a_root wired into wiped_root_any; reuses rm_wipe_detect.is_wipe_root + normalise_operand (imported, not redefined) 2. ✓ TestFindBasedWipes.test_deleting_find_at_a_root_is_blocked: 11 idioms incl find/-delete, find.-delete, find -delete(default .), -exec rm -rf {}, -type f -exec rm, -execdir, /-name-scoped, .., -L, /bin/rm, /* — all blocked 3. ✓ test_scoped_or_non_root_find_is_allowed: find .-name'*.pyc'-delete, ./build, src, /var/log/app-name, no-delete-action, ./node_modules — all allowed 4. ✓ test_find_and_rm_share_one_root_judge: /,..,/./,// all is_wipe_root AND blocked via find — single judge, no drift 5. ✓ scoped verify (high) test_powershell_channel PASS (113); full suite 5990 passed 24 skipped 0 failed 0 warnings 6. ✓ Residual STATED in docstring + CHANGELOG: xargs/sh -c wrappers and non-rm exec verbs uncovered (not silent) 7. ✓ NEGATIVE: find .-name'*.pyc'-delete and find ./subdir -delete NOT blocked (cwd blocks only unscoped; named subdir never a wipe root); non-deleting find never blocked
- 2026-07-26T14:45:17Z [implementation] — AC verified: 1. ✓ danger_patterns._posix_find_wipes_a_root wired into wiped_root_any; reuses imported is_wipe_root+normalise_operand 2. ✓ TestFindBasedWipes block side: 11 idioms blocked 3. ✓ allow side: 8 idioms return None 4. ✓ test_find_and_rm_share_one_root_judge: single is_wipe_root, no drift 5. ✓ scoped verify PASS; full suite 5990 passed 0 failed 0 warnings 6. ✓ residual (xargs/sh -c, non-rm verbs) stated in docstring+CHANGELOG 7. ✓ NEGATIVE: scoped cwd find + named subdir NOT blocked; non-deleting find never blocked
