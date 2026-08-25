---
slug: v156-p2-task-quick-ac
title: "P2: task quick UX — добавить --ac/--acceptance в task_quick (QG-0 не ослаблять)"
status: done
epic: v156
story: v156-kilo-zai-finetune
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/service_task_team.py (task_quick), scripts/project_parser_task.py (quick subparser), scripts/project_cli_task.py:201 (dispatch), harness/claude/mcp/project/handlers.py (_do_task_quick), harness/claude/mcp/project/tools.py (schema), tests/"
scope_exclude: ".claude/mcp/ (генерируется из harness); backend task_add signature (не трогаем — AC через task_update)"
relevant_files:
  - "scripts/service_task_team.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_tausik_service.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T19:27:12Z"
---

## Goal

task_quick (project_cli_task.py:201, сигнатура task_quick(title,goal,role,stack)) должна принимать --ac/--acceptance, чтобы одной командой создать задачу с AC и сразу пройти QG-0. QG-0 НЕ ослаблять — без AC поведение прежнее.

## Acceptance Criteria

1. CLI `task quick <title> --ac "..."` (и алиас --acceptance) создаёт задачу с acceptance_criteria, выставленным на задаче. 2. task_quick(title,goal,role,stack,acceptance=None) — acceptance опционален; реализация: task_add как раньше + task_update(acceptance_criteria=...) когда передан. 3. MCP-паритет: tausik_task_quick принимает acceptance (handlers + tools schema, harness-источник). 4. QG-0 НЕ ослаблен: без --ac задача создаётся как прежде (AC пустой), task_start по-прежнему требует goal+AC. 5. НЕГАТИВНЫЙ: пустая/пробельная строка --ac не создаёт «фейковый» AC (трактуется как отсутствие — task_start всё равно потребует реальный AC) ИЛИ отклоняется; задача с реальным --ac проходит QG-0 после добавления goal.

## Plan

[{"step": "task_quick: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c acceptance \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440 + task_update(acceptance_criteria) \u043a\u043e\u0433\u0434\u0430 \u043d\u0435\u043f\u0443\u0441\u0442\u043e\u0439", "done": true}, {"step": "project_parser_task.py: --ac/--acceptance \u0432 quick subparser (dest=acceptance)", "done": true}, {"step": "project_cli_task.py:201: \u043f\u0440\u043e\u043a\u0438\u043d\u0443\u0442\u044c args.acceptance", "done": true}, {"step": "MCP-\u043f\u0430\u0440\u0438\u0442\u0435\u0442: handlers._do_task_quick + tools.py schema (harness)", "done": true}, {"step": "\u0421\u043c\u043e\u043a + 4 \u044e\u043d\u0438\u0442-\u0442\u0435\u0441\u0442\u0430 (set AC, blank ignored, omit unchanged, QG-0 start)", "done": true}, {"step": "\u0420\u0435\u043a\u043e\u043d\u0441\u0430\u0439\u043b doc-constants + README test_count", "done": true}]

## Rollback

git revert — изменение аддитивно (новый опциональный параметр), без миграций БД.

## Journal

- 2026-06-19T19:27:11Z [implementation] — AC verified: AC-1: ✓ CLI `task quick <title> --ac "..."` (+алиас --acceptance) создаёт задачу с AC — смок: task show показал acceptance_criteria="1. ok 2. negative: rejects empty"; help показывает `--ac ACCEPTANCE, --acceptance ACCEPTANCE`. AC-2: ✓ task_quick(...,acceptance=None): task_add как прежде + task_update(acceptance_criteria) когда acceptance.strip() — test_task_quick_with_acceptance_sets_ac PASSED. AC-3: ✓ MCP-паритет: _do_task_quick прокидывает args.get("acceptance"); tools.py schema получил acceptance-property; test_mcp_integration 64 passed. AC-4: ✓ QG-0 не ослаблен: без --ac AC пустой (test_task_quick_without_acceptance_unchanged); goal+ac через quick → task_start проходит QG-0 (test_task_quick_acceptance_enables_qg0_start). AC-5: ✓ НЕГАТИВНЫЙ: пробельный --ac игнорируется, AC остаётся пустым (test_task_quick_blank_acceptance_leaves_ac_empty + смок). Domain: единая команда даёт QG-0-ready задачу (goal+AC) — реальный UX-выигрыш из боевого отчёта. tests/test_tausik_service.py task_quick: 7 passed (4 новых); doc-constants+README реконсайл 4416→4420. Примечание: .claude/scripts (generated) синхронизируется на rebuild при релизе — правки в источнике scripts/+harness/.
