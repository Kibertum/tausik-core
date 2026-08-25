---
slug: v14-readme-functionality-table
title: "README EN+RU: упростить intro + добавить таблицу функционала"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "README.md, README.ru.md — intro + Functionality + Advanced Features"
scope_exclude: "docs/, scripts/, CHANGELOG, любой код"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T09:20:08Z"
---

## Goal

Текущий intro («Three messages. Full engineering cycle.») маркетинговый и не отвечает на «что это». Заменить на 3-4 предложения plain English/RU + аналогию (например «Git для AI workflow с quality gates»). Добавить новую секцию «Functionality» — структурированная таблица фич по категориям: Lifecycle, Quality Gates, Knowledge/Memory, Verification, Hooks, Multi-IDE, Metrics, Brain, Batch, Skills. Сократить «What's Inside» список (он дублирует таблицу). Anti-Drift / Memory Discipline / Shared Brain секции — упростить или объединить под «Advanced features» с ссылками на docs.

## Acceptance Criteria

1. README.md строки 13-14 заменены на 6 строк plain English + аналогия "Git for AI workflow".
2. README.md перед «What You Get» добавлена `## Functionality` таблица (12 категорий).
3. README.md «Anti-Drift» + «Memory Discipline» + «Shared Brain» заменены на одну `## Advanced Features` (4 буллета со ссылками).
4. README.ru.md — зеркальная переработка по тем же позициям.
5. Negative: «What You Get», «How It Works», «Supported IDEs», «Dogfooding», «Documentation» НЕ трогаются.
6. Negative: badges, license, существующие docs ссылки сохраняются.
7. Visual flow: первый экран читателя — intro → Functionality table → Try It Now (wow effect).
relevant_files: README.md, README.ru.md

## Plan

## Rollback

## Journal

- 2026-05-03T09:20:08Z [implementation] — AC verified: 1. ✓ README.md intro заменён (10 строк plain English + Git-аналогия). 2. ✓ Functionality table 12 категорий перед What You Get. 3. ✓ Anti-Drift+Memory Discipline+Shared Brain → Advanced Features (5 буллетов со ссылками). 4. ✓ README.ru.md зеркальная переработка. 5. ✓ Negative: What You Get/How It Works/Supported IDEs/Dogfooding/Documentation не тронуты. 6. ✓ Negative: badges и license сохранены. 7. ✓ First-screen flow: badges → intro → Functionality table → Try It Now (wow-effect).
