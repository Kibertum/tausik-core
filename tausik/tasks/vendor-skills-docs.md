---
slug: vendor-skills-docs
title: "Vendor skills: example config, документация, bootstrap onboarding"
status: done
epic: polish
story: arch-fixes
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - skills.example.json
  - ".gitignore"
  - "bootstrap/bootstrap.py"
  - "docs/vendor-skills.md"
  - README.md
  - README.en.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:28:17Z"
---

## Goal

skills.json разделён на example и рабочий конфиг. Документация vendor-скиллов для сообщества. Bootstrap --init копирует example. Новый пользователь понимает как подключить свой vendor.

## Acceptance Criteria

1. skills.example.json в git с 5 vendor-ами и комментариями. 2. skills.json в .gitignore. 3. bootstrap --init копирует example → skills.json если не существует. 4. docs/vendor-skills.md описывает формат, все поля, примеры. 5. README содержит секцию Ecosystem/Vendor Skills. 6. Ошибка если skills.json в git tracked.

## Plan

[{"step": "\u041f\u0435\u0440\u0435\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u0442\u044c skills.json \u2192 skills.example.json", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c skills.json \u0432 .gitignore", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c bootstrap.py \u2014init: \u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c example \u2192 skills.json", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c docs/vendor-skills.md \u0441 \u043f\u043e\u043b\u043d\u044b\u043c \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u0435\u043c \u0444\u043e\u0440\u043c\u0430\u0442\u0430", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u0435\u043a\u0446\u0438\u044e Ecosystem \u0432 README.md \u0438 README.en.md", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b", "done": true}]

## Rollback

## Journal

- 2026-04-05T19:28:10Z [implementation] — AC verified: 1. skills.example.json в git ✓ 2. skills.json в .gitignore ✓ 3. bootstrap копирует example→skills.json ✓ 4. docs/vendor-skills.md полный гайд ✓ 5. README RU+EN имеют секцию Ecosystem ✓ 6. 700/700 тестов ✓
