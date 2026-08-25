---
slug: fake-test-detect
title: "Fake test detection в testing agent и /test"
status: done
epic: ralphex-inspired
story: review-overhaul
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/claude/skills/review/agents/testing.md, agents/claude/skills/test/SKILL.md"
scope_exclude: null
relevant_files:
  - "agents/claude/skills/review/agents/testing.md"
  - "agents/claude/skills/test/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-29T17:23:18Z"
---

## Goal

Testing review agent и /test skill обнаруживают фейковые тесты: пустые assertions, хардкод expected=actual, conditional assertions, skip без причины, закомментированные кейсы.

## Acceptance Criteria

1. Testing review agent проверяет: тесты без assertions, assert expected==expected (хардкод), conditional assertions (if False: assert), @skip без причины, закомментированные тест-кейсы. 2. /test skill при генерации тестов предупреждает если сгенерированный тест попадает под fake-паттерн. 3. Каждый найденный fake test — HIGH severity issue. 4. Negative: обычный @skip с причиной НЕ считается fake test.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u0435\u043a\u0446\u0438\u044e Fake Test Detection \u0432 testing.md agent", "done": true}, {"step": "\u041e\u043f\u0438\u0441\u0430\u0442\u044c 5 \u043f\u0430\u0442\u0442\u0435\u0440\u043d\u043e\u0432: no assertions, hardcoded expected, conditional, skip, commented", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u0435 \u0432 /test SKILL.md \u043f\u0440\u0438 \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u0438 \u0442\u0435\u0441\u0442\u043e\u0432", "done": true}, {"step": "\u0423\u043a\u0430\u0437\u0430\u0442\u044c severity HIGH \u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e fake test finding", "done": true}]

## Rollback

## Journal
