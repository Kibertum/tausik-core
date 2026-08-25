---
slug: smart-model-routing
title: "Smart model routing по complexity (Haiku/Sonnet/Opus)"
status: done
epic: claude-hardening
story: p3-nice-to-have
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/model_routing.py (новый), scripts/project_parser.py (suggest-model subcommand), scripts/project_cli_ops.py (handler), bootstrap/bootstrap_templates.py (doc), tests/test_model_routing.py"
scope_exclude: "Автопереключение моделей невозможно в Claude Code CLI — только рекомендации"
relevant_files:
  - "scripts/model_routing.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_model_routing.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T23:42:14Z"
---

## Goal

Задачи simple → Haiku, medium → Sonnet, complex → Opus. Экономия 30-50% токенов (из oh-my-claudecode). Интеграция с slash commands

## Acceptance Criteria

1) Функция suggest_model(complexity) в новом модуле scripts/model_routing.py: simple→Haiku, medium→Sonnet, complex→Opus. Возвращает dict {model_name, display_name, rationale}. 2) CLI `.tausik/tausik suggest-model <complexity>` выводит рекомендацию. 3) Документация в bootstrap_templates.py (Workflow или отдельная секция) о cost-aware model selection. 4) pytest test_model_routing.py: 4+ тестов для каждой complexity + unknown complexity → error message. 5) pytest all passed. 6) ruff clean. Negative: (a) complexity=None → возвращает Sonnet (default) с rationale. (b) unknown string → warning с suggestions. (c) case-insensitive matching.

## Plan

[{"step": "scripts/model_routing.py + suggest_model()", "done": true}, {"step": "CLI suggest-model subcommand", "done": true}, {"step": "Doc \u0432 bootstrap_templates", "done": true}, {"step": "tests + pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T23:35:41Z [implementation] — AC verified: AC1 (suggest_model()) ✓ — scripts/model_routing.py: simple→Haiku 4.5, medium→Sonnet 4.6, complex→Opus 4.7, с dict {model, display, rationale}. AC2 (CLI suggest-model) ✓ — subparser + cmd_suggest_model в project_cli_ops.py, dispatch в project.py. AC3 (документация) ✓ — bootstrap_templates.py WORKFLOW расширен про cost-aware model selection. AC4 (4+ тестов) ✓ — 9 тестов: simple/medium/complex mapping, None default, unknown fallback, case-insensitive, whitespace, one-line format, stable keys. AC5 (pytest) ✓ — 9/9 passed. AC6 (ruff clean) ✓. Negative: (a) None → Sonnet default с "not specified". (b) unknown "gigantic" → Sonnet с "unknown complexity" warning. (c) CASE и whitespace normalized.
