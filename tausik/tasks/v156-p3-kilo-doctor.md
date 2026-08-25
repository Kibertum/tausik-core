---
slug: v156-p3-kilo-doctor
title: "P3: tausik doctor — валидность .kilo/kilo.jsonc + .kilocode/mcp.json, резолв python/command (нужен живой Kilo)"
status: done
epic: v156
story: v156-kilo-zai-finetune
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/service_doctor_kilo.py (новый чек), scripts/project_cli_doctor.py (вызов), tests/"
scope_exclude: "авто-диагностика «MCP tools недоступны» на живом билде (нужен live Kilo); правка bootstrap_kilo"
relevant_files:
  - "scripts/service_doctor_kilo.py"
  - "scripts/project_cli_doctor.py"
  - "tests/test_doctor_kilo.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T19:46:26Z"
---

## Goal

doctor проверяет валидность .kilo/kilo.jsonc + .kilocode/mcp.json и резолвится ли python/command; док «перезапусти Kilo»; сверить формат command-массива с актуальной Kilo; диагностировать «MCP tools недоступны» на живом билде. ОТЛОЖЕНО — требует живого Kilo.

## Acceptance Criteria

1. tausik doctor добавляет Kilo-чек, который запускается ТОЛЬКО при наличии .kilo/ или .kilocode/ (kilo-инсталл): валидирует каждый существующий конфиг (.kilo/kilo.jsonc, .kilocode/mcp.json) — парсится как JSON/JSONC, есть mcp-станза с tausik-project, command — непустой массив, server.py (после резолва ${workspaceFolder}) существует. 2. Невалидный JSON → FAIL; отсутствие mcp-станзы или tausik-project → WARN с подсказкой `bootstrap --ide kilo`; оба конфига отсутствуют при наличии .kilo → WARN. 3. Подсказка «перезапусти Kilo, чтобы перечитать MCP» при любой проблеме. 4. Не-kilo проект (нет .kilo/.kilocode) → чек тихо пропускается. 5. НЕГАТИВНЫЙ кейс: битый/невалидный JSONC → доктор репортит Ошибку FAIL (exit 1), НЕ падает с трейсбеком (graceful). Формат command-массива сверен с bootstrap_kilo (живой Kilo не нужен для структурной валидации — blind).

## Plan

[{"step": "service_doctor_kilo.py: check_kilo_config (gate on .kilo/.kilocode, JSONC-tolerant \u043f\u0430\u0440\u0441, mcp/tausik-project/command/server.py/${workspaceFolder})", "done": true}, {"step": "project_cli_doctor.py: \u0432\u044b\u0437\u043e\u0432 \u0447\u0435\u043a\u0430 \u0441 \u043f\u043e\u0434\u0441\u0447\u0451\u0442\u043e\u043c fail/warn, graceful try/except", "done": true}, {"step": "11 \u044e\u043d\u0438\u0442-\u0442\u0435\u0441\u0442\u043e\u0432 (\u0432\u0430\u043b\u0438\u0434/\u0431\u0438\u0442\u044b\u0439/\u043d\u0435\u0442 mcp/\u043d\u0435\u0442 server/disabled/jsonc/skip)", "done": true}, {"step": "\u0418\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f-\u0441\u043c\u043e\u043a: repo .kilo \u2192 OK; \u0431\u0438\u0442\u044b\u0439 temp \u2192 FAIL+restart hint; filesize OK (322/149)", "done": true}]

## Rollback

git revert — новый модуль + один блок в doctor; чек гейтится на наличие .kilo, не влияет на не-kilo проекты.

## Journal

- 2026-06-19T19:46:25Z [implementation] — AC verified: AC-1: ✓ check_kilo_config гейтится на .kilo/.kilocode; валидирует JSON/JSONC, mcp-станзу с tausik-project, command как непустой массив [python,server.py,...], резолв server.py через ${workspaceFolder} (test_valid_config_ok, test_workspacefolder_resolved). AC-2: ✓ невалидный JSON→FAIL (test_invalid_json_fails); нет mcp→WARN (test_missing_mcp_stanza_warns); нет tausik-project→WARN (test_missing_project_server_warns); .kilo без конфигов→WARN bootstrap --ide kilo (test_kilo_dir_without_config_warns). AC-3: ✓ все detail содержат "restart Kilo" hint. AC-4: ✓ не-kilo проект → check_kilo_config возвращает [] (test_non_kilo_project_skipped); смок doctor в repo с реальными .kilo/.kilocode → обе OK. AC-5: ✓ НЕГАТИВНЫЙ: битый JSONC → FAIL, graceful (try/except в _load_jsonc + cmd_doctor wrapper), exit 1 — смок temp-проект показал "FAIL ... invalid JSON/JSONC ... restart Kilo", без трейсбека. Domain: структура command-массива сверена с bootstrap_kilo._build_mcp_servers (актуальный emit); blind-валидация структуры без живого Kilo. tests/test_doctor_kilo.py 11 passed; filesize 322/149 (<400). Примечание: «MCP tools недоступны» на живом билде требует live Kilo — вне scope (отложено).
