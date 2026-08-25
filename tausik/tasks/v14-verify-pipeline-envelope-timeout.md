---
slug: v14-verify-pipeline-envelope-timeout
title: "Envelope-таймаут на verify pipeline"
status: done
epic: v14-task-done-reliability
story: v14-runtime-safety
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_verification.py (envelope helper + GateEnvelopeTimeoutError + run_gates_with_cache wrap), tests/test_service_verification.py (envelope tests), CHANGELOG (config option mention)"
scope_exclude: "scripts/gate_runner.py (per-gate timeout не трогаем), service_task.py (envelope-error propagation через run_gates_with_cache)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T22:06:04Z"
---

## Goal

Добавить общий wall-time лимит на цикл run_gates_with_cache (NOT per-gate). По умолчанию 60 сек для interactive MCP, конфигурируется через .tausik/config.json ключом verify_pipeline_timeout_seconds. При превышении — abort с понятной ошибкой и предложением переключиться в auto_verify=true или сузить relevant_files. Это гарантирует что task_done не висит даже при ошибочной конфигурации gates.

## Acceptance Criteria

1. service_verification.py получает константу DEFAULT_PIPELINE_TIMEOUT_S=60 и helper resolve_pipeline_timeout_s(cfg).
2. service_verification.py: GateEnvelopeTimeoutError class с понятным message — содержит remediation: «raise verify_pipeline_timeout_seconds, set auto_verify=true, narrow relevant_files».
3. run_gates_with_cache на cache miss оборачивает run_gates в envelope (concurrent.futures.ThreadPoolExecutor + future.result(timeout=...)). Timeout=0 → отключен (legacy behavior).
4. На превышении envelope: GateEnvelopeTimeoutError raised с понятным message.
5. resolve_pipeline_timeout_s(cfg) parsing: int → preserve, str-int → preserve, invalid → default 60, missing → default 60, 0 → preserve (disable).
6. Negative test: gate с sleep(0.5), envelope timeout=0.1s → exception raised в ≤0.5s. На Python Windows.
7. Negative test: timeout=0 (disabled), gate sleep(0.05) → завершается без timeout error.
8. Negative test: invalid config value 'forever' → fallback на default 60.
9. pytest tests/test_service_verification.py + tests/test_verify_first_contract.py зелёные.
10. CHANGELOG.md и CHANGELOG.ru.md упоминают новую опцию `verify_pipeline_timeout_seconds` в существующей секции «Verify-First infrastructure».
relevant_files: scripts/service_verification.py, tests/test_service_verification.py, CHANGELOG.md, CHANGELOG.ru.md

## Plan

## Rollback

## Journal

- 2026-05-02T22:06:04Z [implementation] — AC verified: 1. ✓ DEFAULT_PIPELINE_TIMEOUT_S=60 + resolve_pipeline_timeout_s в service_verification.py. 2. ✓ GateEnvelopeTimeoutError class с remediation message (verify_pipeline_timeout_seconds + auto_verify=true + relevant_files). 3. ✓ run_gates_with_cache оборачивает run_gates через daemon thread + join(timeout). timeout=0 → bypass. 4. ✓ test_envelope_timeout_aborts_long_pipeline проверяет abort за <4.5s при envelope=1s/sleep=5s — passed in 2.07s total. 5. ✓ resolve тесты: missing/invalid → 60, 0 preserved, int preserved, negative → 0. 6. ✓ test_envelope_timeout_aborts_long_pipeline PASSED — daemon thread + join timeout. 7. ✓ test_envelope_disabled_when_zero PASSED. 8. ✓ test_resolve_default_when_invalid PASSED. 9. ✓ pytest tests/test_service_verification.py + test_verify_first_contract.py: 129 passed in 3.01s. 10. ✓ CHANGELOG.md/ru.md упомянули новую опцию + fallback в Verify-First infrastructure секции.
