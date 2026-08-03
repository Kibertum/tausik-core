---
slug: backlog-orphans-invisible-to-roadmap
title: "Девятнадцать сирот бэклога разложить по историям: невидимы для roadmap и для охвата релиза"
status: planning
epic: arch-debt-post-18
story: adp18-quality-signals
complexity: simple
role: architect
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Аудит сессии #158 насчитал 20 задач вне эпиков; одну релизную (brain-move-deletes-leave-ghost-projection) я привязал сразу, остаётся 19. Доктор про них говорит прямо: невидимы для roadmap и для task list --epic, охват релиза считает их отсутствующими.

Состав известен: четыре задачи [2.0] (проекция, элиситация, авторизация, осиротевшие рёбра), три [1.9] (мастер Notion, четыре проверки приватности, накладные расходы прогона), остальные — накопленные дефекты (дрейф доков после #152, ruff-format без гейта, окно калибровки, TAUSIK_HOME без валидации, формат тегов общей базы, cache_status=git-mismatch и прочие).

Причина у большинства одна и уже заведена отдельно: MCP молча выбрасывал параметр story. Эта задача убирает ПОСЛЕДСТВИЯ, mcp-server-drops-unknown-arguments-silently убирает ПРИЧИНУ; закрывать последствия раньше причины бессмысленно — сироты появятся снова.

КРИТЕРИИ: 1) tausik doctor не выдаёт предупреждение backlog hygiene; 2) ни одна задача не переехала в историю, к которой не относится по существу — перенос ради тишины доктора хуже сироты; 3) НЕГАТИВНЫЙ: если подходящей истории нет, задача заводится честно, а не приписывается к ближайшей.

## Acceptance Criteria

## Plan

## Rollback

task move обратимо: перенос задачи между историями не трогает её содержимое

## Journal
