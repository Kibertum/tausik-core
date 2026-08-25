---
slug: rewrite-claude-md-template
title: "Переписать шаблон CLAUDE.md в bootstrap_generate (load-bearing)"
status: done
epic: claude-hardening
story: p0-foundation-rewrite
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "bootstrap/bootstrap_generate.py (функция generate_claude_md), tests/ (новый тест на шаблон)"
scope_exclude: "generate_agents_md и generate_cursorrules — они в задаче sync-agents-md-cursorrules. Dogfooding CLAUDE.md в корне — не трогать."
relevant_files:
  - "bootstrap/bootstrap_generate.py"
  - "tests/test_bootstrap_generate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T20:00:50Z"
---

## Goal

Генерируемый CLAUDE.md для клиентских проектов должен содержать жёсткие ограничения, MCP-first, SENAR rules, workflow граф — чтобы Claude не плавал в новом проекте

## Acceptance Criteria

1) generate_claude_md в bootstrap_generate.py выдаёт 80-150 строк (против текущих ~30). 2) Шаблон содержит секции: Hard Constraints (Нет кода без задачи, Нет коммита без gates, MCP-first, Git ask-first), Workflow Graph (start→plan→task→review→commit→end), Memory Types (TAUSIK vs Claude auto), SENAR Rules Reference, Quality Gates pointer, <!-- DYNAMIC:START/END --> блок. 3) Универсальность: нет упоминаний scripts/, CLI/Service/Backend (это dogfooding-specific). 4) Новый pytest-тест проверяет наличие ключевых маркеров ("Нет кода без задачи"/"No code without task", "MCP-first", "QG-0", "<!-- DYNAMIC"). 5) Все существующие pytest тесты проходят. 6) Ruff clean. Negative/boundary cases: (a) если CLAUDE.md уже существует в проекте — функция НЕ перезаписывает (сохранить текущее поведение). (b) Если stacks=[] (стек не определён) — шаблон всё равно генерится валидно (без пустых скобок / упоминания "not detected" рендерится корректно). (c) Если project_name содержит спецсимволы или пустая строка — генерация не падает.

## Plan

[{"step": "\u041f\u0440\u043e\u0447\u0438\u0442\u0430\u0442\u044c dogfooding CLAUDE.md \u2014 \u0432\u044b\u0434\u0435\u043b\u0438\u0442\u044c \u0443\u043d\u0438\u0432\u0435\u0440\u0441\u0430\u043b\u044c\u043d\u044b\u0435 \u0431\u043b\u043e\u043a\u0438 vs project-specific", "done": true}, {"step": "\u041d\u0430\u0431\u0440\u043e\u0441\u0430\u0442\u044c \u043d\u043e\u0432\u044b\u0439 \u0448\u0430\u0431\u043b\u043e\u043d (80-150 \u0441\u0442\u0440\u043e\u043a) \u0441 Hard Constraints, Workflow Graph, Memory Types, SENAR Rules, Quality Gates pointer", "done": true}, {"step": "\u0417\u0430\u043c\u0435\u043d\u0438\u0442\u044c generate_claude_md \u0432 bootstrap_generate.py", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c pytest \u0442\u0435\u0441\u0442 \u043d\u0430 \u043a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043c\u0430\u0440\u043a\u0435\u0440\u044b (tests/test_bootstrap_generate.py)", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c bootstrap \u043d\u0430 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u043c \u043f\u0440\u043e\u0435\u043a\u0442\u0435 (\u0432 /tmp \u0438\u043b\u0438 tests/fixtures) \u0438 \u0433\u043b\u0430\u0437\u0430\u043c\u0438 \u043f\u043e\u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c \u0432\u044b\u0432\u043e\u0434", "done": true}, {"step": "pytest tests/ -v + ruff check", "done": true}, {"step": "task log \u0441 evidence + task done --ac-verified", "done": true}]

## Rollback

## Journal

- 2026-04-16T19:57:30Z [implementation] — AC-verification evidence: (1) новый generate_claude_md в bootstrap/bootstrap_generate.py:156-281, 106 строк сгенерированного CLAUDE.md (в диапазоне 80-150). (2) Секции: Hard Constraints (13 пунктов), Workflow graph, Memory types table, SENAR Rules table (9 правил), Commands Quick Reference, Quality Gates, External Skills, Roles, Response Language, DYNAMIC block. (3) Универсальность: тест test_no_dogfooding_leakage проверяет отсутствие "CLI → Service → Backend", "project_backend.py", "scripts/project.py", "dogfooding". (4) tests/test_bootstrap_generate.py — 11 тестов, все passed. (5) pytest tests/ -q: 929 passed in 195s. (6) ruff check bootstrap/bootstrap_generate.py tests/test_bootstrap_generate.py: All checks passed. (7) Negative: test_preserves_existing_file / test_empty_stacks_renders_not_detected / test_special_chars_in_project_name / test_empty_project_name — все зелёные. (8) Smoke-test bootstrap в /tmp/tausik-smoke: CLAUDE.md сгенерирован корректно, 106 строк, "Project: my-project", "Stack: not detected". (9) bootstrap_generate.py = 357 строк (под лимитом 400).
- 2026-04-16T19:57:41Z [implementation] — AC verified: AC1 (80-150 строк) ✓ — smoke-test показал 106 строк, тест test_line_count_in_range зелёный. AC2 (Hard Constraints, Workflow Graph, Memory Types, SENAR Rules, Quality Gates, DYNAMIC block) ✓ — test_contains_hard_constraints + test_contains_workflow_and_memory_sections + test_contains_senar_rules_table + test_contains_dynamic_block все passed. AC3 (универсальность, нет scripts/, CLI/Service/Backend) ✓ — test_no_dogfooding_leakage passed. AC4 (pytest-тест на маркеры) ✓ — tests/test_bootstrap_generate.py создан, 11 тестов, все зелёные. AC5 (все existing pytest passed) ✓ — 929 passed in 195s. AC6 (ruff clean) ✓ — "All checks passed!". Negative AC (a) сохранение существующего файла ✓ — test_preserves_existing_file. (b) stacks=[] корректно ✓ — test_empty_stacks_renders_not_detected. (c) спецсимволы/пустой name ✓ — test_special_chars_in_project_name + test_empty_project_name.
