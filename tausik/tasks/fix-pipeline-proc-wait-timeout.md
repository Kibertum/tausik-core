---
slug: fix-pipeline-proc-wait-timeout
title: "[bug] _exec_pipeline: промежуточные proc.wait() без timeout — потенциальный hang многостадийного гейта"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_command_runner.py"
  - "tests/test_gate_pipeline_reap.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T13:49:05Z"
---

## Goal

В gate_command_runner._exec_pipeline строки 152-153 промежуточные proc.wait() без timeout; если промежуточный процесс не завершится, многостадийный pipeline-гейт зависнет. Single-stage путь робастен (DEVNULL+timeout). Добавить timeout/kill на промежуточные процессы.

## Acceptance Criteria

AC1: Промежуточные proc.wait() в _exec_pipeline (после успешного communicate последней стадии) ограничены timeout — никогда не блокируются бесконечно.
AC2 (negative): если промежуточная стадия игнорирует SIGPIPE/не завершается, pipeline НЕ виснет навсегда — proc.wait(timeout) истекает → proc.kill() → wait, выполнение продолжается (bounded). Покрыто новым тестом с фейковой долго-живущей промежуточной стадией.
AC3: happy-path не сломан — single-stage и многостадийный pipeline возвращают прежний (rc, output); существующие тесты gate_command_runner зелёные; ruff + pytest PASS.

## Plan

## Rollback

## Journal

- 2026-06-13T13:48:55Z [implementation] — Fix: _exec_pipeline intermediate reap (procs[:-1]) now proc.wait(timeout=timeout)+kill on TimeoutExpired — bounded, no infinite hang. Test tests/test_gate_pipeline_reap.py: hang-сценарий (SIGPIPE-ignoring sleep(30) stage, timeout=3) возвращается за ~3s (<15s assert); happy-path 2-stage rc/output корректны. 31 passed, ruff clean.
- 2026-06-13T13:49:04Z [implementation] — AC1 ✓: procs[:-1] reap теперь proc.wait(timeout=timeout) — bounded (gate_command_runner.py:152-159). AC2 ✓ (negative): test_hanging_intermediate_stage_does_not_wedge_the_gate — SIGPIPE-ignoring sleep(30) промежуточная стадия, timeout=3 → возврат за ~3s (assert <15s), kill сработал. AC3 ✓: test_multi_stage_happy_path_returns_last_stage_output (rc=0, out='3'); 31 passed; ruff clean; verify (hadolint+pytest) PASS.
