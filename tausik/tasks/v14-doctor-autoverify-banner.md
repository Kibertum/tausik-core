---
slug: v14-doctor-autoverify-banner
title: "doctor показывает жёлтый banner при auto_verify=true"
status: done
epic: v14-task-done-reliability
story: v14-runtime-safety
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_doctor_auto_verify_hint.py — добавить integration test (без правок в project_cli_doctor.py — functionality уже работает)"
scope_exclude: "scripts/project_cli_doctor.py (logic не трогаем, только подтверждаем поведение)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T21:59:03Z"
---

## Goal

tausik doctor должен в первой видимой секции (не в advanced) показывать жёлтое предупреждение если в .tausik/config.json найден task_done.auto_verify=true и не CI environment. Сейчас auto_verify_interactive_warning_detail в project_cli_doctor.py:45 существует, но не surface'ится в реальном doctor output. Добавить интеграционный тест.

## Acceptance Criteria

1. Verified: auto_verify_interactive_warning_detail УЖЕ вызывается в doctor (project_cli_doctor.py:213-216) и SURFACES yellow warning «WARN  Verify-First profile  task_done.auto_verify=true — heavy gates inline...» — подтверждено ручным тестом.
2. Добавить integration test (tests/test_doctor_auto_verify_hint.py) который запускает cmd_doctor (или subprocess) с auto_verify=true и проверяет что stdout содержит "Verify-First profile" + "auto_verify=true".
3. Test покрывает negative: с auto_verify=false / unset → warning НЕ выводится.
4. Test покрывает negative: с CI env → warning НЕ выводится (suppression check).
5. Negative: pytest tests/test_doctor_auto_verify_hint.py зелёный (включая существующие 6 unit тестов + новые integration).
6. Negative: Banner расположен между «Config knobs» и «Quality gates» (видимая основная секция, не advanced).
relevant_files: tests/test_doctor_auto_verify_hint.py

## Plan

## Rollback

## Journal

- 2026-05-02T21:59:02Z [implementation] — AC verified: 1. ✓ Functionality УЖЕ работает в HEAD (project_cli_doctor.py:213-216 surface'ит yellow warning). 2. ✓ Integration test добавлен: _run_doctor_capture(cfg, env) запускает cmd_doctor через patch project_config.load_config + patch.dict os.environ. 3. ✓ test_doctor_surfaces_warning_when_auto_verify_true PASSED (positive). 4. ✓ test_doctor_omits_warning_when_auto_verify_false PASSED (negative — auto_verify=False). 5. ✓ test_doctor_suppresses_warning_in_ci PASSED (negative — env CI=true). 6. ✓ pytest: 10/10 passed in 0.12s. Banner расположен между Config knobs и Quality gates (видимая основная секция, не advanced).
