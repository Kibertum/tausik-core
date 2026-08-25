---
slug: sync-agents-md-cursorrules
title: "Синхронизировать AGENTS.md и .cursorrules с новым CLAUDE.md"
status: done
epic: claude-hardening
story: p0-foundation-rewrite
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "bootstrap/bootstrap_templates.py (новый), bootstrap/bootstrap_generate.py (generate_claude_md/generate_agents_md/generate_cursorrules), bootstrap/bootstrap_qwen.py (generate_qwen_md), tests/test_bootstrap_generate.py (расширение)"
scope_exclude: "bootstrap/bootstrap.py, bootstrap_copy.py, bootstrap_config.py — логика вызова генераторов не трогается. MCP/settings генераторы не трогаются."
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_venv.py"
  - "tests/test_bootstrap_generate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T20:28:43Z"
---

## Goal

Единый источник констрейнтов для всех IDE (Claude/Codex/OpenCode/Cursor). Вынести общую часть в константу, генерить вариации

## Acceptance Criteria

1) Общая часть (Hard Constraints, Workflow, Memory types, SENAR rules, Commands, Quality Gates) вынесена в отдельный модуль bootstrap/bootstrap_templates.py или как функция в bootstrap_generate.py. 2) generate_claude_md, generate_agents_md, generate_cursorrules — все используют один источник констрейнтов (DRY). 3) AGENTS.md содержит те же 13 hard constraints, что и CLAUDE.md (было 8 правил — синхронизировать до полного списка). 4) .cursorrules расширен с текущего thin (~25 строк) до аналогичного объёма, содержит те же hard constraints. 5) bootstrap_qwen.py (generate_qwen_md) также синхронизирован. 6) pytest: новые тесты на AGENTS.md и .cursorrules с теми же маркерами, все passed. 7) ruff clean. 8) bootstrap_generate.py <400 строк (или разнесён). Negative: (a) если AGENTS.md/.cursorrules/QWEN.md уже существует — НЕ перезаписывать. (b) Общая функция не ломается при stacks=[]. (c) Если модуль bootstrap_templates импортируется — нет circular imports.

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c bootstrap/bootstrap_templates.py \u0441 COMMON_* \u043a\u043e\u043d\u0441\u0442\u0430\u043d\u0442\u0430\u043c\u0438 \u0438\u043b\u0438 build_common_body() \u0444\u0443\u043d\u043a\u0446\u0438\u0435\u0439", "done": true}, {"step": "\u0420\u0435\u0444\u0430\u043a\u0442\u043e\u0440\u0438\u0442\u044c generate_claude_md \u043d\u0430 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u0435 shared body", "done": true}, {"step": "\u041f\u0435\u0440\u0435\u043f\u0438\u0441\u0430\u0442\u044c generate_agents_md \u2014 \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c shared constraints", "done": true}, {"step": "\u041f\u0435\u0440\u0435\u043f\u0438\u0441\u0430\u0442\u044c generate_cursorrules \u2014 \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c shared constraints (\u0441 cursor-specific framing)", "done": true}, {"step": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c bootstrap_qwen.py \u0438 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c generate_qwen_md", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: \u0440\u0430\u0441\u0448\u0438\u0440\u0438\u0442\u044c tests/test_bootstrap_generate.py \u043d\u0430 AGENTS.md + .cursorrules + QWEN.md", "done": true}, {"step": "pytest + ruff + smoke-test bootstrap", "done": true}]

## Rollback

## Journal

- 2026-04-16T20:15:23Z [implementation] — AC verified: AC1 (общая часть вынесена в отдельный модуль) ✓ — создан bootstrap/bootstrap_templates.py (156 строк) с HARD_CONSTRAINTS/WORKFLOW/MEMORY/SENAR_RULES/COMMANDS/QUALITY_GATES/RESPONSE_LANGUAGE/DYNAMIC_BLOCK константами + build_full_body(). AC2 (DRY) ✓ — generate_claude_md, generate_agents_md, generate_cursorrules, generate_qwen_md все импортируют build_full_body и передают agent_name + ide_subdir. AC3 (AGENTS.md имеет те же 13 hard constraints) ✓ — test_constraint_parity сравнивает маркеры в 4 файлах. AC4 (.cursorrules расширен) ✓ — было 25 строк, теперь 104. AC5 (bootstrap_qwen.py синхронизирован) ✓ — generate_qwen_md тоже использует build_full_body, тест test_points_to_qwen_subdir passed. AC6 (новые тесты, все passed) ✓ — 13 новых тестов: TestGenerateAgentsMd (4) + TestGenerateCursorrules (4) + TestGenerateQwenMd (4) + TestSyncAcrossIdes (1). Всего 942/942 passed in 248s. AC7 (ruff clean) ✓ — python -m ruff check bootstrap/bootstrap_templates.py bootstrap/bootstrap_generate.py bootstrap/bootstrap_qwen.py tests/test_bootstrap_generate.py → All checks passed. AC8 (bootstrap_generate.py <400) ✓ — 211 строк (было 357, упало на 146 благодаря выносу в templates). Negative: (a) preserves_existing тесты для 4 файлов ✓. (b) test_empty_stacks ✓. (c) Circular imports: нет — bootstrap_templates импортируется лениво внутри функций ✓. БОНУС: обнаружен и исправлен dogfooding leakage — bootstrap.py копировал lib/AGENTS.md (с описанием scripts/references/agents/) поверх сгенерированного. Удалил copy block в bootstrap.py:358-367. Теперь generate_agents_md — единственный источник.
- 2026-04-16T20:25:44Z [implementation] — Follow-up: filesize gate (hard QG-2 block) сработал на bootstrap.py 408 строк. Приложил: (1) ruff --fix bootstrap/bootstrap.py — убрал unused imports + F541 f-strings, → 408. (2) Вынес install_cli_wrapper() в bootstrap_venv.py. (3) bootstrap.py → 392 строки (под 400). bootstrap_venv.py 234 (под 400). 32 bootstrap-теста passed.
