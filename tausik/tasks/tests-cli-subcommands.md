---
slug: tests-cli-subcommands
title: "Smoke-тесты для непокрытых CLI subcommands"
status: done
epic: polish
story: test-gaps
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_cli_smoke_extra.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:37:20Z"
---

## Goal

CLI subcommands team, roadmap, metrics, dead-end, explore, audit, run имеют smoke-тесты. Return codes и базовый output проверяются.

## Acceptance Criteria

1. Smoke-тесты для team, roadmap, metrics, dead-end, explore, audit. 2. Каждый проверяет return code 0 и наличие ожидаемого substring в output. 3. Минимум 8 новых тестов. 4. Ошибка если subcommand возвращает non-zero без причины.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c smoke-\u0442\u0435\u0441\u0442 team subcommand", "done": false}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c smoke-\u0442\u0435\u0441\u0442\u044b roadmap, metrics", "done": false}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c smoke-\u0442\u0435\u0441\u0442\u044b dead-end, explore", "done": false}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c smoke-\u0442\u0435\u0441\u0442\u044b audit, gates status", "done": false}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0432\u0441\u0435 CLI \u0442\u0435\u0441\u0442\u044b", "done": false}]

## Rollback

## Journal

- 2026-04-05T19:37:11Z [implementation] — AC verified: 12 smoke тестов для team/roadmap/metrics/dead-end/explore/audit/gates ✓
