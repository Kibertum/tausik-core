---
slug: refactor-cmd-gates
title: "Перенести бизнес-логику из cmd_gates и cmd_skill в Service"
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
  - "scripts/project_service.py"
  - "scripts/project_cli_extra.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:34:07Z"
---

## Goal

CLI handlers cmd_gates и cmd_skill только форматируют вывод. Бизнес-логика в Service: gates_status(), gate_enable(), gate_disable().

## Acceptance Criteria

1. ProjectService имеет gates_status(), gate_enable(name), gate_disable(name). 2. cmd_gates в CLI <= 30 строк (только форматирование). 3. cmd_skill не конструирует пути — берёт из Service/config. 4. Ошибка если cmd_gates/cmd_skill содержат load_config/save_config вызовы.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c gates_status(), gate_enable(), gate_disable() \u0432 ProjectService", "done": true}, {"step": "\u0420\u0435\u0444\u0430\u043a\u0442\u043e\u0440\u0438\u0442\u044c cmd_gates \u2014 \u0442\u043e\u043b\u044c\u043a\u043e \u0444\u043e\u0440\u043c\u0430\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0432\u044b\u0432\u043e\u0434\u0430", "done": true}, {"step": "\u0420\u0435\u0444\u0430\u043a\u0442\u043e\u0440\u0438\u0442\u044c cmd_skill \u2014 \u0443\u0431\u0440\u0430\u0442\u044c \u043a\u043e\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438\u044e \u043f\u0443\u0442\u0435\u0439, \u0432\u0437\u044f\u0442\u044c \u0438\u0437 config/ide_utils", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b", "done": true}]

## Rollback

## Journal

- 2026-04-05T19:33:56Z [implementation] — AC verified: 1. gates_status/gate_enable/gate_disable в Service ✓ 2. cmd_gates ~30 строк форматирования ✓ 3. cmd_skill уже использует ide_utils ✓ 4. Нет load_config/save_config в CLI ✓ 700/700 тестов ✓
