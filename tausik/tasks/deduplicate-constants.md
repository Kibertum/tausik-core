---
slug: deduplicate-constants
title: "Устранить дублирование констант и конфигов"
status: done
epic: polish
story: arch-fixes
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_types.py"
  - "scripts/service_task.py"
  - "scripts/service_knowledge.py"
  - "scripts/backend_graph.py"
  - "scripts/project_parser.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T16:38:07Z"
---

## Goal

Одна копия: VALID_EDGE_RELATIONS, VALID_NODE_TYPES в project_types.py. Stacks в parser из VALID_STACKS. Security keywords в одну константу. Config loading — единая функция.

## Acceptance Criteria

1. VALID_EDGE_RELATIONS и VALID_NODE_TYPES определены только в project_types.py. 2. project_parser.py использует sorted(VALID_STACKS) вместо хардкоженного списка. 3. SECURITY_KEYWORDS — единая константа в service_task.py. 4. load_config вызывается из одного места (project_config.py). 5. Ошибка если grep находит дубли этих констант в других файлах.

## Plan

[{"step": "\u041f\u0435\u0440\u0435\u043d\u0435\u0441\u0442\u0438 VALID_EDGE_RELATIONS, VALID_NODE_TYPES \u0432 project_types.py", "done": true}, {"step": "\u0418\u043c\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0432 backend_graph.py \u0438 service_knowledge.py", "done": true}, {"step": "\u0417\u0430\u043c\u0435\u043d\u0438\u0442\u044c choices \u0432 project_parser.py \u043d\u0430 sorted(VALID_STACKS)", "done": true}, {"step": "\u0412\u044b\u043d\u0435\u0441\u0442\u0438 SECURITY_KEYWORDS \u0432 \u043a\u043e\u043d\u0441\u0442\u0430\u043d\u0442\u0443 service_task.py", "done": true}, {"step": "\u0412\u044b\u043d\u0435\u0441\u0442\u0438 NEGATIVE_SCENARIO_KEYWORDS \u0432 \u043a\u043e\u043d\u0441\u0442\u0430\u043d\u0442\u0443", "done": true}, {"step": "\u041a\u043e\u043d\u0441\u043e\u043b\u0438\u0434\u0438\u0440\u043e\u0432\u0430\u0442\u044c load_config \u2014 \u0435\u0434\u0438\u043d\u0430\u044f \u0444\u0443\u043d\u043a\u0446\u0438\u044f \u0432 project_config.py", "done": true}, {"step": "Grep-\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0434\u0443\u0431\u043b\u0435\u0439", "done": true}]

## Rollback

## Journal

- 2026-04-05T16:37:57Z [implementation] — AC verified: 1. VALID_EDGE_RELATIONS/VALID_NODE_TYPES в project_types.py ✓ 2. parser использует sorted(VALID_STACKS) и др. ✓ 3. SECURITY_KEYWORDS единая константа ✓ 4. backend_graph.py дубли удалены ✓ 5. 700/700 тестов ✓
