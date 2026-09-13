---
slug: update-claudemd-writes-session-state-into-a-tracked-agents-md
title: "GitLab #14: update-claudemd пишет DYNAMIC-блок (сессия, ветка, хвост памяти, чужие знания) в версионируемый AGENTS.md безусловно — грязное дерево и предупреждение, которое нечем снять"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-host-parity-refactors
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/claudemd_writer.py, scripts/project_config.py, tests/, docs/en/configuration.md, docs/ru/configuration.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Тикет GitLab #14 (владелец, kibertum-org на 1.8.0): claudemd_writer.resolve_sibling_targets добавляет AGENTS.md к целям DYNAMIC-записи, если он существует; в проекте, где CLAUDE.md сознательно выведен из-под git ради автообновления, AGENTS.md остаётся версионируемым — и туда каждую сессию попадают номер сессии, ветка, счётчики, хвост памяти и «Shared knowledge — from other projects». Следствия: `M AGENTS.md` после одного /start; WARN «undeclared: AGENTS.md» в каждой квитанции verify, который нельзя снять честно; история либо засоряется, либо расходится; знание чужих проектов уезжает в историю репозитория. Тикет предлагает три варианта (писать DYNAMIC только в первичный файл; ручка `claudemd.sibling_dynamic: false`; писать в сиблинг только то, что осмысленно в свежем клоне). Это выбор поведения, а не правка одной строки — решение #366 выносит его в 1.10. Задача: принять вариант (рекомендация — ручка с умолчанием «как сейчас» ПЛЮС усечённый блок в сиблинге без чужих знаний), реализовать, покрыть тестами обе ветки ручки и мутацией «ручка игнорируется», задокументировать в configuration.md EN/RU, ответить в тикете.

## Acceptance Criteria

AC-1: выбран и записан решением вариант поведения сиблинга (ручка / только первичный / усечённый блок); умолчание не ломает существующие проекты. AC-2: при выключенной ручке AGENTS.md не получает DYNAMIC-блока; при включённой — прежнее поведение; оба пути покрыты тестом на временном проекте. AC-3: «Shared knowledge — from other projects» не пишется в версионируемый сиблинг ни при каком значении ручки, если выбран усечённый вариант. AC-4: мутация — ручка читается, но игнорируется — краснит тест. AC-5: docs/{en,ru}/configuration.md описывают ручку; CHANGELOG EN/RU; ответ в GitLab #14. AC-6: signed verify.

## Plan

## Rollback

git revert; ручка исчезает, сиблинг снова получает полный блок.

## Journal
