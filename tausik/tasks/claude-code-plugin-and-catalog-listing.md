---
slug: claude-code-plugin-and-catalog-listing
title: "Плагин Claude Code и заявка в официальный каталог Anthropic"
status: planning
epic: visibility-stream
story: entry-barrier
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "bootstrap/**"
  - ".claude-plugin/**"
  - "docs/**"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

TAUSIK ставится командой /plugin install, не покидая Claude Code, и присутствует в каталоге, который смотрят при выборе инструмента.

## Acceptance Criteria

1. `/plugin marketplace add Kibertum/tausik-core` и `/plugin install tausik` работают на чистой машине; проверено запуском, а не чтением документации.
2. Заявка подана в anthropics/claude-plugins-official — каталог на 33 435 звёзд с открытым приёмом заявок.
3. Плагин при первом запуске инициализирует базу сам либо ЯВНО говорит, какой одной командой это сделать. Молчаливо нерабочая установка ЗАПРЕЩЕНА.
4. НЕГАТИВНЫЙ сценарий: если модель плагинов не покрывает весь bootstrap, плагин ставит лёгкий слой и НАЗЫВАЕТ то, чего в нём нет, а не делает вид, что установка полная.
5. ЗАВИСИМОСТЬ: публикуется ПОСЛЕ hooks-point-into-a-submodule-a-plain-clone-does-not-have. Приводить людей во фреймворк, где не работает ни один хук, — потратить единственный первый шанс.

## Plan

## Rollback

Плагин снимается с публикации; остальные каналы не затронуты

## Journal
