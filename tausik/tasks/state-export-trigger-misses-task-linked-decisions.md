---
slug: state-export-trigger-misses-task-linked-decisions
title: "Авто-экспорт состояния не срабатывает на task-linked decisions и task_update — headline-фича релиза протекает"
status: planning
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Обнаружено в сессии #152 при записи решения #202 об объёме релиза 1.8.

ВОСПРОИЗВЕДЕНО ЗАПУСКОМ, не чтением. Записал решение с task_slug -> `Decision #202 recorded — saved to local`. `git status` чист по tausik/decisions/, файлов 201 при 202 решениях, grep по тексту решения в дереве пуст. После ручного `.tausik/tausik state export` файл появился (202 файла) и вместе с ним всплыла ещё и незаэкспортированная правка tausik/tasks/brain-decide-publishes-unclassified-rationale.md.

ПРИЧИНА ПО КОДУ. scripts/service_knowledge.py::decide имеет три ветки возврата. auto_export_by_id вызывается ТОЛЬКО в последней (локальная запись без task_slug). Ранний возврат `if task_slug is not None` пишет строку в БД и возвращается БЕЗ экспорта. Ветка успешной записи в brain не пишет локально вообще (см. смежную задачу brain-decide-publishes-unclassified-rationale, AC0). Аналогично не экспортируется task_update.

ПОЧЕМУ ЭТО ВАЖНО ИМЕННО СЕЙЧАС. Состояние-в-git — headline-фича, которой релиз 1.8 представлен в README EN+RU. Большинство решений проекта пишутся С task_slug, то есть по самому частому пути фича молчаливо не работает. Дыру маскирует периодический полный `state export`: он подтягивает пропущенное, поэтому `tausik status` не показывает расхождения, и на глаз всё выглядит согласованным. В команде это значит, что коллега после git pull не увидит решений, записанных с момента последнего ручного экспорта.

НЕ дефект (чтобы следующий агент не искал заново): memory_add экспортируется корректно — два файла в tausik/memory/ появились сразу после записи, без ручного экспорта.

## Acceptance Criteria

## Plan

## Rollback

## Journal
