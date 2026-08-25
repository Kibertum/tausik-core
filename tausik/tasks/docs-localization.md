---
slug: docs-localization
title: "Стратегия локализации и EN-версии ключевых docs"
status: done
epic: public-release
story: docs-audit
complexity: complex
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.en.md
  - README.md
  - "references/QUICKSTART.en.md"
  - "references/architecture.en.md"
  - "docs/i18n-strategy.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T13:39:40Z"
---

## Goal

README, QUICKSTART, architecture — имеют EN-версии. Стратегия i18n задокументирована. Международный разработчик может onboard-иться без русского.

## Acceptance Criteria

1. README.en.md существует — EN версия README. 2. references/QUICKSTART.en.md существует. 3. references/architecture.en.md существует. 4. Стратегия i18n задокументирована в docs/i18n-strategy.md. 5. Ошибка если EN-версия не содержит всех секций из RU-оригинала.

## Plan

[{"step": "\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c \u0441\u0442\u0440\u0430\u0442\u0435\u0433\u0438\u044e i18n: \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u044b\u0435 \u0444\u0430\u0439\u043b\u044b (*.en.md) vs \u043f\u0430\u043f\u043a\u0438 (docs/en/)", "done": true}, {"step": "\u041f\u0435\u0440\u0435\u0432\u0435\u0441\u0442\u0438 README.md \u2192 README.en.md", "done": true}, {"step": "\u041f\u0435\u0440\u0435\u0432\u0435\u0441\u0442\u0438 QUICKSTART.md \u2192 QUICKSTART.en.md", "done": true}, {"step": "\u041f\u0435\u0440\u0435\u0432\u0435\u0441\u0442\u0438 architecture.md \u2192 architecture.en.md", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c language switcher \u0432 README (\ud83c\uddf7\ud83c\uddfa/\ud83c\uddec\ud83c\udde7)", "done": true}, {"step": "\u0417\u0430\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0442\u0440\u0430\u0442\u0435\u0433\u0438\u044e \u043b\u043e\u043a\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0438 \u0432 docs/i18n-strategy.md", "done": true}, {"step": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c onboarding \u043f\u0443\u0442\u044c \u0434\u043b\u044f EN-\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f", "done": true}]

## Rollback

## Journal

- 2026-04-05T13:39:34Z [implementation] — AC verified: 1. README.en.md ✓ 2. QUICKSTART.en.md ✓ 3. architecture.en.md ✓ 4. docs/i18n-strategy.md ✓ 5. Все секции из RU-оригиналов присутствуют в EN-версиях ✓
