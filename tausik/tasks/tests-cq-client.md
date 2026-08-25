---
slug: tests-cq-client
title: "Тесты для cq_client.py + URL scheme валидация"
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
  - "scripts/cq_client.py"
  - "tests/test_cq_client.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:37:19Z"
---

## Goal

cq_client.py покрыт тестами (mock-based). URL scheme валидируется (только http/https). SSRF-вектор закрыт.

## Acceptance Criteria

1. test_cq_client.py существует с mock-based тестами. 2. Покрыты: query, propose, health, _request. 3. URL scheme валидация добавлена (только http/https). 4. Тест: file:// URL → ValueError. 5. Ошибка если cq_client принимает file:// endpoint.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c URL scheme \u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u044e \u0432 cq_client.py __init__", "done": false}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c test_cq_client.py: mock urllib \u0434\u043b\u044f query/propose/health", "done": false}, {"step": "\u0422\u0435\u0441\u0442: file:// URL \u2192 ValueError", "done": false}, {"step": "\u0422\u0435\u0441\u0442: graceful degradation \u043f\u0440\u0438 connection error", "done": false}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b", "done": false}]

## Rollback

## Journal

- 2026-04-05T19:37:10Z [implementation] — AC verified: 16 тестов, URL scheme валидация добавлена, file:// → ValueError ✓
