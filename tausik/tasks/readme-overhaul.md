---
slug: readme-overhaul
title: "README overhaul for public release audience"
status: done
epic: null
story: null
complexity: complex
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "README.md, README.ru.md"
scope_exclude: "docs/, references/, scripts/, agents/, bootstrap/"
relevant_files:
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-08T16:13:29Z"
---

## Goal

Переработать README.md и README.ru.md для новой аудитории: чёткое позиционирование, объяснение терминов, quickstart без загадок, визуальный порядок секций, call to action

## Acceptance Criteria

1. Одно предложение "что это" сразу после бейджей
2. Целевая аудитория указана явно
3. --smart и --init объяснены или упрощены в quickstart
4. MCP tools и skills определены перед использованием чисел
5. Dogfooding секция перемещена после Key Features
6. Codex в IDE таблице честно описан (ограниченная поддержка)
7. Next Steps / call to action в конце README
8. RU: "шлюзы качества" заменены на "quality gates" или "контрольные точки"
9. RU: "слой инженерного управления" переписан естественно
10. RU: "экран команд" заменён на понятный термин
11. Ошибка в переводе "15 проверок с учётом языка" исправлена
12. Methodology секция сокращена до ссылки без повторов
13. README.ru.md синхронизирован с README.md по структуре

## Plan

## Rollback

## Journal

- 2026-04-08T16:10:41Z [implementation] — AC verified: 1. One-sentence def after badges [v] 2. Target audience stated [v] 3. --smart/--init explained [v] 4. MCP tools and skills defined in "How It Works" before numbers [v] 5. Dogfooding moved after Key Features [v] 6. Codex honestly described [v] 7. Next Steps CTA at end [v] 8. RU: quality gates kept as English term [v] 9. RU: "фреймворк инженерного контроля" [v] 10. RU: "фильтр команд" [v] 11. RU: "15 проверок для вашего стека" [v] 12. Methodology condensed to 2 sentences + link [v] 13. RU synced with EN structure [v]
