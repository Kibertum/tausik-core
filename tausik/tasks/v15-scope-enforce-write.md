---
slug: v15-scope-enforce-write
title: "[P0] PreToolUse блокирует запись вне scope"
status: done
epic: v15-evidence-attestation
story: v15-scope-acl
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/scope_acl.py"
  - "scripts/hooks/scope_write_gate.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "tests/test_scope_write_gate_hook.py"
  - "tests/test_bootstrap_hooks_parity.py"
scope_paths:
  - "scripts/scope_acl.py"
  - "scripts/hooks/scope_write_gate.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "tests/*"
scope_tools:
  - Edit
  - Write
  - Bash
depends_on: []
completed_at: "2026-06-12T01:11:59Z"
---

## Goal

PreToolUse-хук сверяет путь Write/Edit с scope активной задачи; запись вне декларированного scope блокируется (exit 2) с понятным сообщением. ACL-энфорсмент по паттерну Walko.

## Acceptance Criteria

1. PreToolUse hook scope_write_gate.py: Write/Edit/MultiEdit вне scope_paths активной задачи -> exit 2 + сообщение (задача, ACL, как расширить). 2. Разрешено: нет активной задачи с scope_paths (legacy), путь вне project_dir, путь матчится ACL любой активной задачи (union). 3. Негативный: путь вне ACL -> блок; scope_paths='[]' -> блок любой записи в проект. 4. Fail-open: ошибка/битая БД -> allow (exit 0); TAUSIK_HOOK_FAIL_SECURE=1 -> block. 5. Хук зарегистрирован в bootstrap_hooks + bootstrap_qwen (parity test). 6. pytest: match_path glob-семантика + hook allow/block/fail-open/skip-env.

## Plan

## Rollback

git revert + re-bootstrap убирает хук из settings.json; мгновенный обход без отката: TAUSIK_SKIP_HOOKS=1; хук fail-open по умолчанию (ошибка БД не блокирует запись), задачи без scope_paths не затрагиваются вовсе

## Journal

- 2026-06-12T01:11:45Z [implementation] — Impl: match_path в scope_acl, hook scope_write_gate.py, регистрация claude+qwen, parity pin; live smoke: out-of-ACL=2, tests/*=0, in-ACL=0; 44+53 tests
- 2026-06-12T01:11:58Z [implementation] — AC verified: 1. OK live smoke: Write scripts/project_cli_verify.py (вне ACL) -> exit 2 + BLOCKED msg с задачей/ACL/remediation. 2. OK tests: no_active/undeclared-legacy/outside-root/union allow; live in-ACL paths exit 0. 3. OK test_write_outside_scope_blocked + test_explicit_empty_acl_blocks_everything. 4. OK test_pre_v30_schema_fails_open + test_pre_v30_schema_fail_secure_blocks. 5. OK registered in bootstrap_hooks + bootstrap_qwen, parity test pin, 53 passed. 6. OK pytest tests/test_scope_write_gate_hook.py + test_scope_acl.py 44 passed.
- 2026-06-12T01:12:17Z [done] — AC-1: ✓ tested via tests/test_scope_write_gate_hook.py::TestHook::test_write_outside_scope_blocked; AC-2: ✓ test_union_across_active_tasks + test_undeclared_active_task_grants_legacy_freedom + test_outside_project_root_allowed; AC-3 Negative: ✓ test_explicit_empty_acl_blocks_everything + test_corrupt_acl_json_treated_as_empty_blocks; AC-4 Negative: ✓ test_pre_v30_schema_fails_open + test_pre_v30_schema_fail_secure_blocks; AC-5: ✓ tests/test_bootstrap_hooks_parity.py::test_critical_hooks_present_in_both; AC-6: ✓ TestMatchPath 14 параметров
