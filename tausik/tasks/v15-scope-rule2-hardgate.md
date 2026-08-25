---
slug: v15-scope-rule2-hardgate
title: "[P1] SENAR Rule 2 (Scope) warning → hard gate"
status: done
epic: v15-evidence-attestation
story: v15-scope-acl
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_qg0_check.py + tests/test_rule6_rollback.py/test_qg2_gates.py + новый тест"
scope_exclude: "service_gates.py (394/400 строк, не трогать), keyword-эвристики SECURITY_*"
relevant_files:
  - "scripts/gate_qg0_check.py"
  - "tests/test_rule2_scope_hardgate.py"
  - "tests/test_rule6_rollback.py"
  - "tests/test_task_start_model_banner.py"
scope_paths:
  - "scripts/gate_qg0_check.py"
  - "tests/*"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-06-12T01:20:58Z"
---

## Goal

Перевести Rule 2 (Scope) из warning-only в hard gate на базе декларированного scope (вместо keyword-эвристики с FP-риском). Конфиг для opt-out, тесты на FP/FN.

## Acceptance Criteria

1. Негативный: явная medium/complex задача БЕЗ scope-декларации (ни scope_paths, ни legacy scope) -> ошибка ServiceError на task start (блок) с подсказкой --scope-paths/--scope. 2. scope_paths declared (включая []) ИЛИ непустой legacy scope -> старт проходит; unset complexity/simple -> warning-only (как было). 3. Негативный: config qg0.scope_hard_gate=false -> warning вместо ошибки (opt-out). 4. FP-регрессия: существующие Rule6/QG-0 тесты с legacy scope зелёные (test_rule6_rollback + test_qg2_gates). 5. pytest: hard/soft/opt-out/legacy-compat.

## Plan

## Rollback

git revert; мгновенный opt-out без отката: .tausik/config.json qg0.scope_hard_gate=false возвращает warning-only поведение; legacy free-text scope продолжает удовлетворять гейту (обратная совместимость)

## Journal

- 2026-06-12T01:20:48Z [implementation] — AC-1 Negative: ✓ tests/test_rule2_scope_hardgate.py::TestHardGate (3 теста, блок без scope); AC-2: ✓ TestDeclarationSatisfies + TestSoftPaths; AC-3 Negative: ✓ test_opt_out_config_downgrades_to_warning + TestConfigResolution; AC-4: ✓ test_rule6_rollback/test_qg2_gates/полный suite 3450 passed (2 фикса сетапа тестов + доки-константы 3580 + README badges); AC-5: ✓ 13 новых тестов
- 2026-06-12T01:20:57Z [implementation] — AC verified: 1. OK блок без scope (TestHardGate). 2. OK scope_paths/legacy scope/[] проходят, simple/unset warning-only. 3. OK opt-out конфигом. 4. OK регрессия: full suite 3450 passed. 5. OK 13 тестов.
