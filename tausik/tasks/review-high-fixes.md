---
slug: review-high-fixes
title: "Fix 5 HIGH review findings (gate whitelist + shell + race + multi-agent + hook matcher)"
status: done
epic: v131-review-fixes
story: high-findings
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_config.py (ALLOWED_GATE_EXECUTABLES + _validate_custom_gate)\nscripts/hooks/task_call_counter.py (multi-active loop + BEGIN IMMEDIATE)\nscripts/service_recording.py (race documentation if needed)\nbootstrap/bootstrap_generate.py (matcher Write|Edit|MultiEdit|Bash)\n.claude/settings.json (mirror)\ntests/test_review_high_fixes.py (новый)\ntests/test_agent_units_recording.py (обновить multi-active assumption)"
scope_exclude: "scripts/service_task.py (только если race fix требует — стараемся не трогать; transaction уже atomic)\nscripts/gate_runner.py (shell=True logic не меняется — только validator tightens)\nagents/skills/* (не трогаем)\ndefault_gates.py (gates уже добавлены прошлой сессией; whitelist отдельно)"
relevant_files:
  - "scripts/project_config.py"
  - "scripts/hooks/task_call_counter.py"
  - "bootstrap/bootstrap_generate.py"
  - ".claude/settings.json"
  - "tests/test_review_high_fixes.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T14:17:56Z"
---

## Goal

Close 5 HIGH-severity findings from the v1.3.x post-Epic-2 multi-agent review: (1) extend ALLOWED_GATE_EXECUTABLES with IaC tools so user overrides aren't silently rejected; (2) tighten _validate_custom_gate to block shell metachars regardless of {files} placeholder; (3) fix counter clear race between task_done and PostToolUse hook; (4) PostToolUse hook should count toward all active tasks (not no-op when >1); (5) restrict PostToolUse matcher to Write/Edit/Bash so Read/Grep don't pollute calibration drift.

## Acceptance Criteria

- [ ] HIGH-1: ALLOWED_GATE_EXECUTABLES (project_config.py) расширен ansible-lint, terraform, helm, kubeval, hadolint, tflint, kube-score; user override команды на vendor/bin/ansible-lint работает (test_validate_custom_gate_iac PASSED)
- [ ] HIGH-2: _validate_custom_gate блокирует shell metachars (`&&`, `||`, `;`, backtick, `$()`) независимо от {files} placeholder; existing legitimate gates остаются valid; новый test_custom_gate_blocks_shell_chars_without_files PASSED
- [ ] HIGH-3: race fix — task_call_counter использует BEGIN IMMEDIATE при инкременте; task_done читает meta_get + clear ВНУТРИ транзакции (уже так) + lock pattern. Best-effort property: counter может быть 0 или N, но не undefined; documented в service_recording.py docstring
- [ ] HIGH-4: PostToolUse hook task_call_counter инкрементирует все active tasks (вместо no-op при >1). Behavior: SELECT slug FROM tasks WHERE status='active' (без LIMIT 2) → for each slug bump counter. test_increments_for_multiple_active PASSED
- [ ] HIGH-5: bootstrap_generate.py + .claude/settings.json mirror — PostToolUse hook task_call_counter получает matcher 'Write|Edit|MultiEdit|Bash' (вместо ''); calibration drift не загрязняется Read/Grep tool calls. test_hook_registered_with_correct_matcher (читает settings.json) PASSED
- [ ] Backwards compat: существующие 200+ tests проходят без модификации
- [ ] Negative scenarios: (a) custom gate с `&&` reject; (b) hook без active task — graceful no-op (как было); (c) multi-active increment работает в new test; (d) ALLOWED whitelist legacy executables всё ещё validate как раньше
- [ ] Tests: новый файл tests/test_review_high_fixes.py с минимум 5 тестами по каждому HIGH; обновить tests/test_agent_units_recording.py для multi-active branch и matcher

## Plan

## Rollback

## Journal

- 2026-04-25T14:17:54Z [implementation] — AC verified: 1. HIGH-1: ALLOWED_GATE_EXECUTABLES + ansible-lint/ansible/terraform/tflint/tofu/helm/kubeval/kube-score/hadolint ✓ (TestIacExecutablesWhitelisted 5+1 PASSED) 2. HIGH-2: _SHELL_CHAIN_PATTERN блокирует &&/||/;/$(/backtick безусловно; pipe оставлен только под {files} guard; стоковые pipe-команды (2>&1 | head) проходят ✓ (TestShellChainBlocked 5+1 PASSED, test_gates 82/82 backwards-compat) 3. HIGH-3: hook использует BEGIN IMMEDIATE + isolation_level=None для serialised lock против task_done транзакций ✓ (test_hook_uses_begin_immediate_in_source PASSED) 4. HIGH-4: hook теперь итерирует ВСЕ active tasks (без LIMIT 2 no-op) ✓ (test_increments_all_active_tasks, test_repeat_call_bumps_each, test_no_active_remains_noop PASSED) 5. HIGH-5: bootstrap_generate.py + .claude/settings.json — matcher='Write|Edit|MultiEdit|Bash' ✓ (test_settings_matcher_excludes_read_only_tools PASSED — Read/Grep/Glob NOT в matcher) 6. Backwards-compat: 251/251 tests across review_high_fixes + agent_units_recording + gates + qg2_gates + tausik_service + tausik_backend 7. Negative scenarios: chain ops без {files} reject ✓; pipe stock pattern allowed ✓; multi-active не-no-op ✓; matcher Read excluded ✓
