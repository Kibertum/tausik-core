---
slug: framework-version-stamp-reads-as-the-products-version
title: "Штамп версии фреймворка стоит в документе продукта без подписи и читается как версия продукта"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/project_cli_extra.py"
  - "scripts/*.py"
  - "harness/**"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Строка состояния в CLAUDE.md продукта не может быть прочитана как утверждение о версии продукта.

## Acceptance Criteria

1. Поле подписано так, что принадлежность фреймворку очевидна без чтения кода (например «TAUSIK: 1.8.0», а не «Version: 1.8.0»).
2. Правка сделана в ОБОИХ местах, печатающих один формат; тикет GitLab #5 называет это отдельной частью дефекта — вторая копия правила. Места перечисляются из кода.
3. Замер тикета назван в тесте: проект версии 0.1.0, чей CLAUDE.md объявляет 1.8.0.
4. НЕГАТИВНЫЙ сценарий: тест на то, что строка НЕ содержит слова, читаемого как версия продукта, — иначе правка сведётся к косметике и вернётся при следующем редактировании формата.

## Plan

## Rollback

git revert коммита; правка в формате строки в двух местах

## Journal
