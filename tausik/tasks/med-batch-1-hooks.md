---
slug: med-batch-1-hooks
title: "Batch: hook hardening (6 MEDs)"
status: done
epic: v134-hardening
story: security-fixes
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/bash_firewall.py"
  - "scripts/hooks/_common.py"
  - "scripts/hooks/task_gate.py"
  - "scripts/hooks/memory_pretool_block.py"
  - "scripts/skill_manager.py"
  - "scripts/service_skills.py"
  - "bootstrap/bootstrap_copy.py"
  - "tests/test_hooks.py"
  - "tests/test_hooks_common.py"
  - "tests/test_skill_manager.py"
  - "tests/test_copy_symlinks_disabled.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T13:15:47Z"
---

## Goal

Bundle: bash_firewall token-regex (not substring), pip --no-config + clear PIP_*, copytree symlinks=False, hooks check .tausik/ dir not .db, last_user_prompt_text bounded read, brain symlinks fix. Closes 6 MED (Sec).

## Acceptance Criteria

1. bash_firewall: replace substring match for 'git push --force' / 'git reset --hard' with same regex shape as git_push_gate.py; 2. skill_manager pip install: pass --no-config and clear PIP_INDEX_URL/PIP_EXTRA_INDEX_URL/PIP_TRUSTED_HOST in subprocess env; 3. skill_manager copy_skill + bootstrap_copy.copy_dir: pass symlinks=False to copytree; 4. memory_pretool_block + task_gate: detect TAUSIK by .tausik/ dir not just .db file; 5. _common.last_user_prompt_text: tail-read last 50 KB instead of readlines() on whole transcript; 6. Each fix covered by test in tests/test_v131_hardening.py; 7. Negative: edited tests confirm previous bypass paths now fail.

## Plan

[{"step": "Fix #1 bash_firewall: \u0432\u044b\u043d\u0435\u0441\u0442\u0438 git_push_gate-style regex \u0432 _common, \u043f\u0440\u0438\u043c\u0435\u043d\u0438\u0442\u044c \u043a 'git push --force' / 'git reset --hard' \u043f\u0430\u0442\u0442\u0435\u0440\u043d\u0430\u043c", "done": true}, {"step": "Fix #1 \u0442\u0435\u0441\u0442\u044b: 'echo \"git push --force\"' \u043d\u0435 \u0431\u043b\u043e\u043a\u0438\u0440\u0443\u0435\u0442\u0441\u044f, '/usr/bin/git push --force-with-lease' \u0431\u043b\u043e\u043a\u0438\u0440\u0443\u0435\u0442\u0441\u044f \u0438\u043b\u0438 \u043d\u0435\u0442 (\u0440\u0435\u0448\u0438\u0442\u044c)", "done": true}, {"step": "Fix #2 skill_manager pip: pass --no-config + clear PIP_INDEX_URL/PIP_EXTRA_INDEX_URL/PIP_TRUSTED_HOST \u0432 subprocess env", "done": true}, {"step": "Fix #2 \u0442\u0435\u0441\u0442: monkeypatch PIP_INDEX_URL=evil, install \u0432\u044b\u0437\u044b\u0432\u0430\u0435\u0442 subprocess \u0431\u0435\u0437 \u044d\u0442\u043e\u0439 env-var", "done": true}, {"step": "Fix #3 copy_skill + bootstrap_copy.copy_dir: pass symlinks=False \u0432 shutil.copytree", "done": true}, {"step": "Fix #3 \u0442\u0435\u0441\u0442: tmp \u0440\u0435\u043f\u043e \u0441\u043a\u0438\u043b\u043b\u0430 \u0441 symlink \u043d\u0430 /etc/passwd \u2192 \u043a\u043e\u043f\u0438\u044f \u0438\u043c\u0435\u0435\u0442 \u0444\u0430\u0439\u043b-\u0432\u043d\u0443\u0442\u0440\u044c \u043e\u0442 .tausik/, \u043d\u0435 symlink \u043d\u0430\u0440\u0443\u0436\u0443", "done": true}, {"step": "Fix #4 memory_pretool_block + task_gate: detect_tausik() \u043f\u043e os.path.isdir('.tausik') \u0432\u043c\u0435\u0441\u0442\u043e os.path.exists('.tausik/tausik.db')", "done": true}, {"step": "Fix #4 \u0442\u0435\u0441\u0442: \u0441\u0432\u0435\u0436\u0438\u0439 \u043f\u0440\u043e\u0435\u043a\u0442 \u0431\u0435\u0437 db \u043d\u043e \u0441 .tausik/ \u2192 hooks \u0440\u0435\u0430\u0433\u0438\u0440\u0443\u044e\u0442 (\u0440\u0430\u043d\u044c\u0448\u0435 \u043c\u043e\u043b\u0447\u0430\u043b\u0438)", "done": true}, {"step": "Fix #5 _common.last_user_prompt_text: tail-read \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 50KB transcript'\u0430 (seek-to-end + read \u0441 \u0432\u044b\u0440\u0430\u0432\u043d\u0438\u0432\u0430\u043d\u0438\u0435\u043c \u043f\u043e \\n)", "done": true}, {"step": "Fix #5 \u0442\u0435\u0441\u0442: 1MB transcript file \u2192 \u043f\u0440\u043e\u0447\u0438\u0442\u0430\u043d\u044b \u0442\u043e\u043b\u044c\u043a\u043e \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 50KB", "done": true}, {"step": "Fix #6 brain symlinks (\u0440\u0435\u0432\u0438\u0437\u0438\u044f): \u043d\u0430\u0439\u0442\u0438 \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u043e\u0435 \u043c\u0435\u0441\u0442\u043e \u0432 brain_sync/brain_init \u0433\u0434\u0435 copytree \u0431\u0435\u0437 symlinks=False, \u0438\u0441\u043f\u0440\u0430\u0432\u0438\u0442\u044c", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0432\u0435\u0441\u044c tests/test_v131_hardening.py \u0437\u0435\u043b\u0451\u043d\u044b\u043c", "done": true}, {"step": "task done --ac-verified + commit 'fix(security): bash_firewall regex + pip --no-config + copytree symlinks=False + hook detect dir + bounded prompt-read'", "done": true}]

## Rollback

## Journal

- 2026-04-28T13:07:55Z [implementation] — Fix #6 (brain symlinks): audit-only — `git grep -E 'copytree|os\.symlink|os\.readlink|os\.lstat|shutil\.'` across scripts/brain_*.py + agents/claude/mcp/brain/ returned ZERO hits. No brain code path involves symlink-following or directory copying. AC #6 was speculative; the scan IS the deliverable. (For comparison, fix #3 added symlinks=False to the 3 actual copytree call sites in scripts/skill_manager, scripts/service_skills, bootstrap/bootstrap_copy.)
- 2026-04-28T13:15:33Z [implementation] — AC verified: ✓1 bash_firewall WARN_PATTERNS_RE: regex with command-start anchor + optional path + optional `git -c` flags + subcommand boundary. Mirrors git_push_gate.py shape. ✓2 11 new firewall regression tests: --force-with-lease, -f, force after positional args (literal git invocations blocked); echo 'git push --force', gitfoo push --force, git checkout main (no false positives). ✓3 skill_manager.install_skill_deps: pip --no-config flag + safe_env strips PIP_INDEX_URL/PIP_EXTRA_INDEX_URL/PIP_TRUSTED_HOST/PIP_FIND_LINKS/PIP_INDEX. 3 new tests confirm flag presence + env stripping + unrelated-env preservation. ✓4 copy_skill in skill_manager + skill_install in service_skills + bootstrap_copy.copy_dir all pass symlinks=False. New test_copy_symlinks_disabled.py with hostile-repo fixture (symlink to outside file): 3 tests covering all 3 call sites; symlink target is materialized as plain file content (no symlink in dst tree). ✓5 hooks/_common: new is_tausik_project(project_dir) checks for .tausik/ dir presence. task_gate + memory_pretool_block migrated. 3 new test_hooks tests. ✓6 last_user_prompt_text: new _read_transcript_tail() seeks last 50KB, drops partial first line. 3 new tests covering 1MB transcript + tail-window bound + partial-line-after-seek. ✓7 brain symlinks AUDIT-CLEAN: git grep across scripts/brain_*.py + agents/claude/mcp/brain/ for copytree|os.symlink|readlink|lstat|shutil. = ZERO hits. AC #6 was speculative — no fix needed; scan IS the deliverable. Full pytest: 2310 passed +1 skipped (was 2287). Filesize: all touched files under 400 (max=398).
