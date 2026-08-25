---
slug: gate-stack-aware-dispatch
title: "[CRITICAL] Stack-aware gate dispatch — stop silent QG-2 bypass"
status: done
epic: enterprise-stack-agnostic
story: stack-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_runner.py (infer_stacks + gate_applies_to + run_gates filter)\nscripts/project_config.py (DEFAULT_GATES.pytest stacks)\ntests/test_gate_stack_aware.py (новый)"
scope_exclude: "scripts/service_*.py (не нужно)\nagents/skills/* (отдельно)\nverification_runs cache wipe (документировать в notes, не делать)\nmulti-stack file detection (per-file ANY-of-stacks реализуется в helper)"
relevant_files:
  - "scripts/gate_runner.py"
  - "scripts/gate_stack_dispatch.py"
  - "scripts/project_config.py"
  - "tests/test_gate_stack_aware.py"
  - "tests/test_gates.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T12:24:22Z"
---

## Goal

Fix critical bug: pytest gate silently passes на не-Python проектах. Add stacks: list[str] к gate def schema. run_gates filter по applicable_stacks (derived из file extensions relevant_files + task.stack hint). Multi-stack files: ANY-of-stacks match runs gate. Когда matching=∅: explicit cache_status='not_applicable', honest warning в task notes/stderr, NOT silent pass. pytest gate получает stacks: ['python', 'fastapi', 'django', 'flask']. Stack-aware fallback в resolve_test_files_for_relevant (file extensions → язык-specific default). Migration: wipe verification_runs (10-min TTL = no real loss). Existing Python tests остаются зелёные (backwards compat). Добавить tests для не-Python проектов: pytest correctly NOT run, status='not_applicable'.

## Acceptance Criteria

- [ ] `stacks: ['python','fastapi','django','flask']` добавлено к DEFAULT_GATES['pytest']
- [ ] gate_runner.infer_stacks_from_files(files) возвращает set из file extensions (.py→python, .ts/.tsx→typescript, .js/.jsx→javascript, .go→go, .rs→rust, .java→java, .kt→kotlin, .php→php, .swift→swift, .dart→flutter)
- [ ] gate_runner.gate_applies_to(gate, files, task_stack) возвращает True если gate.stacks intersect (file_stacks ∪ {task_stack}) или gate без stacks (universal)
- [ ] run_gates: если gate не применим — добавляет result {name, severity, passed=True, output='Not applicable for this stack', skipped=True}; всё ещё honest, не silent (output виден в format_results)
- [ ] format_results: skipped gates показываются как [SKIP] явно
- [ ] Backwards compat: существующие Python-ные тесты остаются зелёные (test_qg2_gates, test_gates)
- [ ] Negative scenarios: relevant_files=[] и task без stack → universal gates run, stack-specific → skipped (file_stacks=∅, task_stack=None); pytest на не-Python project (relevant_files=['main.go']) → SKIP а не silent pass
- [ ] Wipe verification_runs cache (10-min TTL не блокирует) — НЕ внутри миграции, а в этой задаче делается, оставляем для будущей session — записать как dead_end fallback ИЛИ пропустить (cache invalidation — разовая сессия, и сейчас cache empty так как мы только что mass-bumped tests)
- [ ] Tests test_gate_stack_aware.py: (a) infer_stacks_from_files; (b) gate_applies_to с разнымиCombinations; (c) run_gates skipped result с не-Python files; (d) backwards compat — Python relevant_files run pytest; (e) ('not_applicable' status в output)

## Plan

## Rollback

## Journal

- 2026-04-25T12:24:18Z [implementation] — AC verified: 1. pytest gate stacks=['python','fastapi','django','flask'] ✓ (project_config.py + test_pytest_is_stack_gated_to_python PASSED) 2. infer_stacks_from_files maps extensions ✓ (TestInferStacks 14 PASSED) 3. gate_applies_to logic correct ✓ (TestGateApplies 5 PASSED) 4. run_gates filter inserts SKIP results ✓ (TestDispatchFiltering 3 PASSED + skipped_result helper) 5. format_results shows [SKIP] icon ✓ (test_format_results_shows_skip_label PASSED) 6. Backwards compat — Python tests зелёные ✓ (test_gates 82/82, test_qg2_gates 14/14) 7. Negative scenario: pytest на main.go → SKIP не silent ✓ (test_pytest_skipped_for_go_only_files PASSED) 8. verification_runs cache wipe — пропущено (10-min TTL, очистится сама) 9. Tests test_gate_stack_aware.py 24/24 PASSED
