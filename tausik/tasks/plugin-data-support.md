---
slug: plugin-data-support
title: "Поддержка CLAUDE_PLUGIN_DATA для хранения данных"
status: done
epic: claude-hardening
story: p3-nice-to-have
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/plugin_data.py (новый), bootstrap/bootstrap_templates.py (обновление Memory), tests/test_plugin_data.py (новый)"
scope_exclude: "Переписка уже существующих методов, использующих .tausik/ — не трогать (миграция — отдельная задача)"
relevant_files:
  - "scripts/plugin_data.py"
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_plugin_data.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T23:34:07Z"
---

## Goal

Skills используют CLAUDE_PLUGIN_DATA env var вместо директории skill для персистентных данных. Из memory #25

## Acceptance Criteria

1) Утилита scripts/plugin_data.py: функция get_plugin_data_dir() возвращает CLAUDE_PLUGIN_DATA env var если set, иначе fallback на .tausik/plugin_data/. 2) Документация: описано в bootstrap_templates.py (Memory section упомянуть CLAUDE_PLUGIN_DATA). 3) pytest test_plugin_data.py — 4+ тестов: env set → uses it, env unset → fallback, directory created on first use, path is absolute. 4) pytest all passed. 5) ruff clean. Negative: (a) env var с невалидным путём (не существует родителя) → graceful (makedirs exist_ok=True). (b) env var с пустой строкой → fallback на default.

## Plan

[{"step": "scripts/plugin_data.py \u0441 get_plugin_data_dir()", "done": true}, {"step": "tests/test_plugin_data.py", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c bootstrap_templates.py Memory section", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T23:31:11Z [implementation] — AC verified: AC1 (get_plugin_data_dir()) ✓ — scripts/plugin_data.py с env var priority + fallback. AC2 (документация) ✓ — bootstrap_templates.py MEMORY section добавил параграф про CLAUDE_PLUGIN_DATA. AC3 (4+ тестов) ✓ — 6 тестов: env priority, env unset fallback, empty string fallback, absolute path, create=False, idempotent. AC4 (pytest) ✓ — 6/6 passed. AC5 (ruff) ✓ — All checks passed. Negative: (a) невалидный parent в CLAUDE_PLUGIN_DATA → makedirs exist_ok=True не падает (test_makedirs_is_idempotent). (b) empty string → fallback (test_fallback_when_env_empty_string).
