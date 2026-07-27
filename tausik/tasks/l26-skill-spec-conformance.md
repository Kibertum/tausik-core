---
slug: l26-skill-spec-conformance
title: "Валидация скиллов против канонической спеки agentskills.io"
status: planning
epic: landscape-2026-h2
story: l26-ecosystem
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "harness/skills"
  - "scripts/skill_validate.py"
scope_tools: []
completed_at: null
---

## Goal

Спека SKILL.md УШЛА ОТ ANTHROPIC и стала кросс-вендорной: канон теперь agentskills.io/specification, каталог anthropics/skills/spec стал трёхстрочным редиректом, разработка в github.com/agentskills/agentskills, есть референс-валидатор skills-ref validate. Реализуют OpenAI, Google, Microsoft, Cursor, JetBrains, Mistral, AWS, ByteDance, Databricks, Snowflake — войны форматов не случилось. Проверяемые ограничения: name 1-64 символа из a-z0-9 и дефиса, без ведущего/замыкающего дефиса, БЕЗ СДВОЕННЫХ ДЕФИСОВ, и ОБЯЗАНО совпадать с именем родительского каталога; description 1-1024; поля license, compatibility (до 500 символов), metadata, экспериментальное allowed-tools. Прогрессивное раскрытие формализовано в три стадии: метаданные около 100 токенов грузятся на старте для ВСЕХ скиллов, инструкции до 5000 токенов при активации, ресурсы по требованию. Задача: прогнать свои скиллы через референс-валидатор, устранить расхождения, добавить проверку в гейты. ВАЖНО: спека не версионирована и не содержит НИ ОДНОГО положения по безопасности — на неё нельзя опираться в вопросах доверия.

## Acceptance Criteria

AC1. Свои скиллы прогнаны через референс-валидатор skills-ref validate; результат зафиксирован.
AC2. Устранены расхождения с каноном agentskills.io: имя скилла 1-64 символа из a-z0-9 и дефиса, без ведущего/замыкающего/сдвоенного дефиса и совпадает с именем родительского каталога; description 1-1024. Тест-проверка на каждый скилл.
AC3. Проверка соответствия спеке добавлена в гейты: гейт ФЕЙЛИТ на намеренно битом скилле (плохое имя/описание) и молчит на валидных (fails-then-passes).
AC4. В доке/гейте явно помечено, что спека не версионирована и не содержит НИ ОДНОГО положения по безопасности — на неё нельзя опираться в вопросах доверия.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; валидация отключается, скиллы остаются как есть

## Journal
