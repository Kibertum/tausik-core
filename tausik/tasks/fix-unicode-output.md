---
slug: fix-unicode-output
title: "Replace Unicode symbols in CLI output with ASCII-safe alternatives"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_task.py"
  - "scripts/service_gates.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_backend.py"
  - "scripts/project_cli.py"
  - "scripts/project_service.py"
  - "scripts/backend_migrations_legacy.py"
  - "scripts/ide_utils.py"
  - "scripts/service_skills.py"
  - "scripts/backend_crud.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_graph.py"
  - "scripts/backend_queries.py"
  - "scripts/backend_schema.py"
  - "scripts/project.py"
  - "scripts/project_config.py"
  - "scripts/project_parser.py"
  - "scripts/service_knowledge.py"
  - "scripts/service_cascade.py"
  - "scripts/gate_runner.py"
  - "scripts/generate_cli_ref.py"
  - "scripts/skill_manager.py"
  - "scripts/tausik_utils.py"
  - "scripts/project_types.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-08T15:45:23Z"
---

## Goal

Заменить все Unicode-символы (→, ⚠, ✓, ✔, ✅) в print/output строках скриптов на ASCII-safe эквиваленты, чтобы CLI работал на Windows с cp1251 без PYTHONIOENCODING=utf-8

## Acceptance Criteria

1. Все print() и строки выводимые пользователю содержат только ASCII-safe символы
2. Замены: → на ->, ⚠ на WARNING:, ✓/✔/✅ на [v] или оставлены как regex-паттерн для поиска
3. Комментарии и логгер тоже очищены от Unicode
4. Ошибка UnicodeEncodeError не возникает при запуске на Windows cp1251 без PYTHONIOENCODING
5. Тесты проходят

## Plan

## Rollback

## Journal

- 2026-04-08T15:42:30Z [implementation] — AC verified: 1. All print/output strings ASCII-safe [v] 2. Replaced: -> for arrows, WARNING:/[!] for warnings, [v] for checkmarks, -- for em-dashes, \uXXXX for regex [v] 3. Comments and logger cleaned [v] 4. Zero non-ASCII non-Cyrillic chars in all .py files [v] 5. 918 tests pass [v]
