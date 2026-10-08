---
slug: auto-export-proektsiya-dolzhna-rezolvit-derevo-ot-svc-ne-ot
title: "auto_export/проекция должна резолвить дерево от svc, не от ambient cwd — иначе тесты пишут в реальный tausik/"
type: gotcha
tags:
  - auto-export
  - cwd-vs-handle
  - state-git
  - test-isolation
task: state-roundtrip-gate-review-fixes
edges: []
---

state_triggers._tree_root() брал `find_tausik_dir()` (ambient cwd), а не `svc.tausik_dir()`. С включённым state.auto_export ЛЮБАЯ операция (task_done/decide/memory_add) на tmp-БД в тестах, запущенных из реального cwd, писала проекцию в РЕАЛЬНЫЙ tausik/ (появились a-pattern.md, t1.md — слаги, которых нет в реальной БД). Тот же класс, что mcp-config-read-paths-ignore-project-handle. Фикс: _tree_root(svc) от svc.tausik_dir(). Урок: любой путь, зависящий от 'текущего проекта', резолвь от переданного svc/handle, НЕ от cwd — cwd в тестах/MCP != проект операции. Также: тест-fixture, сидящий БД операциями при глобально включённом auto_export, материализует tmp/tausik — отключай auto_export в fixture (monkeypatch _auto_export_enabled→False), если тест проверяет 'нет дерева'. Чистка загрязнения: `tausik state export` реконсилит (removed stale). Связано с [[state-git]].
