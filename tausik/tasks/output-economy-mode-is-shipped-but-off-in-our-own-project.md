---
slug: output-economy-mode-is-shipped-but-off-in-our-own-project
title: "Режим экономии вывода поставляется, а в нашем собственном проекте выключен — догфудинг нарушен"
status: planning
epic: landscape-2026-h2
story: agent-output-discipline
complexity: null
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

В bootstrap_templates.py живут два рычага: output_mode (сжимает ВЫВОД агента, значение caveman) и context_tier (размер впрыскиваемых ПРАВИЛ). В .tausik/config.json этого проекта НЕ УСТАНОВЛЕН НИ ОДИН — оба в умолчании, то есть выключены. Мы поставляем пользователю механизм экономии, которым сами не пользуемся, при заявленном принципе «Dogfooding: этот фреймворк — наш же пользователь». Задача: принять решение по каждому рычагу для ЭТОГО проекта и записать его, а не просто включить. Включение непусто: caveman меняет форму ответов во всех сессиях, а warn_output_mode_not_applied прямо предупреждает, что на уже забутстрапленном проекте флаг НИЧЕГО не меняет на диске — файл правил preserve-if-exists. Значит нужен либо явный путь применения к существующему файлу, либо честное сообщение о том, что требуется. Второй половиной задачи закрыть вопрос, почему собственный проект не проверяет собственные настройки: расхождение «поставляем, но не применяем» должно ловиться, а не обнаруживаться разбором поля.

## Acceptance Criteria

## Plan

## Rollback

## Journal
