---
slug: v15mr-phase-matrix
title: "[P1] Матрица фаза x сложность для выбора модели"
status: done
epic: v15-model-routing
story: v15mr-phase-routing
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/model_routing.py, scripts/model_routing_matrix.py, docs/ru/research/model-routing-matrix.md, tests/*"
scope_exclude: "scripts/project_cli_ops.py, scripts/project_parser_ops.py (CLI --phase surface belongs to v15mr-phase-surfaces), scripts/service_task.py, scripts/external_reviewer.py"
relevant_files:
  - "scripts/model_routing.py"
  - "scripts/model_routing_matrix.py"
  - "docs/ru/research/model-routing-matrix.md"
  - "tests/test_model_routing.py"
  - "tests/test_task_start_model_banner.py"
  - "tests/test_task_next_model_hint.py"
  - "tests/test_model_routing_session.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths:
  - "scripts/model_routing.py"
  - "scripts/model_routing_matrix.py"
  - "docs/ru/research/model-routing-matrix.md"
  - "tests/*"
  - README.md
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-06-14T15:16:52Z"
---

## Goal

Матрица phase x complexity -> модель (Claude-only, ТЗ пользователя): planning -> fable/opus (экономия токенов на планировании за счёт качества плана); implement simple -> sonnet, medium -> sonnet, complex -> opus/fable; research simple -> haiku, research deep -> sonnet. suggest_model(complexity, phase=implement) + config-override + research-док с обоснованием.

## Acceptance Criteria

1. suggest_model принимает phase из {planning, implement, research}; ячейки матрицы соответствуют ТЗ (planning=fable|opus, implement simple=sonnet, implement complex=opus|fable, research simple=haiku). 2. Вызов без phase = implement, поведение текущих потребителей не меняется (обратная совместимость, существующие тесты зелёные). 3. Негативный: неизвестная phase -> ошибка ValueError с перечнем допустимых значений. 4. Конфиг-override (model_routing в .tausik/config.json) + docs/ru/research/model-routing-matrix.md с обоснованием каждой ячейки. 5. pytest: все ячейки + override + негатив.

## Plan

## Rollback

git revert: дефолт (без phase) сохраняет сегодняшнее поведение, потребители не ломаются

## Journal

- 2026-06-14T15:16:51Z [implementation] — AC verified: 1. ✓ Matrix cells match ТЗ via tests/test_model_routing.py::test_matrix_cells (planning_*_fable, implement_simple=sonnet, implement_complex=opus, research_simple=haiku, research_*=sonnet) + _MATRIX in scripts/model_routing_matrix.py 2. ✓ No-phase==implement via test_default_phase_is_implement; back-compat signature via test_implement_mapping + TestSuggestModelStillWorks. DELIBERATE change (Decision #112): implement-simple Haiku->Sonnet; 3 legacy simple->haiku assertions updated, haiku preserved under research-simple (test_matrix_cells::research_simple_haiku) 3. ✓ Negative: unknown phase -> ValueError listing planning/implement/research via tests/test_model_routing.py::test_unknown_phase_raises_valueerror; _normalize_phase in model_routing_matrix.py 4. ✓ Config override (model_routing in .tausik/config.json) via test_config_override_per_tier / _whole_phase_string / _unknown_model_id; research doc docs/ru/research/model-routing-matrix.md justifies every cell + override schema 5. ✓ pytest: 87 passed across tests/test_model_routing.py + banner/hint/session; full suite 4120 green after doc-constants regen (constants.json + README badges)
