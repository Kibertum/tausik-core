---
slug: review-fix-a1-cache-key-includes-cmd
title: "[A1 HIGH] Cache key должен включать резолвенный gate command"
status: done
epic: senar-verify-redesign
story: review-findings-fix
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_verification.py, scripts/project_cli_verify.py, tests/test_service_verification.py"
scope_exclude: "scripts/project_config.py"
relevant_files:
  - "scripts/service_verification.py"
  - "scripts/project_cli_verify.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:18:28Z"
---

## Goal

Multi-agent review: cache_command в service_verification.py:213 — это f'trigger=task-done|files=...' без актуальной gate command строки. Если изменить project_config.DEFAULT_GATES['pytest']['command'] (или [tausik.verify] override), старые зелёные runs остаются в кэше → стэйл-кэш с НОВОЙ командой считается актуальным. Нужно включить hash резолвед gate commands в cache key. Также применить в project_cli_verify.cmd_verify.

## Acceptance Criteria

1. Новая helper resolve_gate_signature(trigger) -> str — возвращает stable hash актуальных gate commands для trigger (читает project_config.get_gates_for_trigger + load_config)
2. cache_command в run_gates_with_cache теперь включает gate_signature: f"trigger=task-done|sig={signature}|files={','.join(sorted(files))}"
3. Аналогичный fix в project_cli_verify.cmd_verify (тот же формат)
4. Регрессия: cache hit на тех же файлах + том же trigger → работает
5. Кейс A1: изменение gate command в config (через monkeypatch) → cache MISS на следующем lookup (signature changed)
6. Ошибка/граничный случай: gate config недоступен / load_config raise → fallback на старую signature (без crash, не блокировать verification)
7. Ошибка/граничный случай: пустой gates set → signature = stable empty marker
8. Тест: test_cache_invalidates_on_gate_command_change
9. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:18:25Z [implementation] — AC verified: ✓1 resolve_gate_signature(trigger) — sha256 over sorted gate command+severity tuples, 16-char hex ✓2 cache_command в run_gates_with_cache теперь f"trigger=task-done|sig={gate_sig}|files=..." ✓3 same fix в project_cli_verify.cmd_verify ✓4 регрессия: existing cache hit tests PASS ✓5 test_signature_changes_when_command_changes: monkeypatch project_config.get_gates_for_trigger с разными commands → разные signatures ✓6 fallback "unavailable" на RuntimeError, "empty" на пустой gates list — test_returns_unavailable_on_load_error + test_returns_empty_when_no_gates_for_trigger ✓7 ✓8 test_cache_invalidates_on_gate_command_change: 1st run miss, change command, 2nd run на тех же файлах — снова miss (не hit) ✓9 pytest 76/76, ruff clean
