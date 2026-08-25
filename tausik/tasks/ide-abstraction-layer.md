---
slug: ide-abstraction-layer
title: "IDE-абстракция: detect_ide, get_ide_target, конфиг-фабрика"
status: done
epic: public-release
story: cross-ide
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/ide_utils.py"
  - "agents/claude/mcp/project/handlers.py"
  - "scripts/project_cli_extra.py"
  - "tests/test_ide_utils.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T13:32:55Z"
---

## Goal

Фреймворк определяет IDE автоматически и генерирует правильные конфиги. Нет хардкоженных путей .claude/ в runtime-коде. Новый IDE добавляется одним файлом-адаптером.

## Acceptance Criteria

1. scripts/ide_utils.py существует с detect_ide(), get_ide_target(), get_skills_dir(). 2. MCP handlers не содержат хардкоженных .claude путей (grep подтверждает). 3. bootstrap_generate.py использует конфиг-фабрику. 4. Тесты покрывают detect_ide для 3 IDE (claude, cursor, generic). 5. Ошибка если detect_ide возвращает невалидный IDE — ValueError. 6. Добавление нового IDE = 1 файл-адаптер без изменения core.

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c scripts/ide_utils.py \u0441 detect_ide(), get_ide_target(), get_skills_dir(), get_ide_config()", "done": true}, {"step": "\u0420\u0435\u0444\u0430\u043a\u0442\u043e\u0440\u0438\u0442\u044c MCP handlers \u2014 \u0437\u0430\u043c\u0435\u043d\u0438\u0442\u044c \u0445\u0430\u0440\u0434\u043a\u043e\u0434 .claude \u043d\u0430 \u0432\u044b\u0437\u043e\u0432\u044b ide_utils", "done": true}, {"step": "\u0420\u0435\u0444\u0430\u043a\u0442\u043e\u0440\u0438\u0442\u044c bootstrap_generate.py \u2014 \u043a\u043e\u043d\u0444\u0438\u0433-\u0444\u0430\u0431\u0440\u0438\u043a\u0430 \u043f\u043e IDE", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b \u0434\u043b\u044f ide_utils (claude, cursor, windsurf, generic)", "done": true}, {"step": "Grep-\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430: \u043d\u0435\u0442 \u0445\u0430\u0440\u0434\u043a\u043e\u0436\u0435\u043d\u043d\u044b\u0445 .claude \u043f\u0443\u0442\u0435\u0439 \u0432 runtime-\u043a\u043e\u0434\u0435", "done": true}]

## Rollback

## Journal

- 2026-04-05T13:32:49Z [implementation] — AC verified: 1. ide_utils.py создан с detect_ide/get_ide_target/get_skills_dir ✓ 2. MCP handlers используют _get_ide_skills_dir() ✓ 3. bootstrap конфиг-фабрика через IDE_REGISTRY ✓ 4. 21 тест, 3 IDE покрыты ✓ 5. ValueError для невалидного IDE ✓ 6. Новый IDE = добавить запись в IDE_REGISTRY ✓
