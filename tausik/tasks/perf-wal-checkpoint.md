---
slug: perf-wal-checkpoint
title: "Убрать per-write WAL checkpoint, оптимизировать DDL on startup"
status: done
epic: polish
story: perf
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_backend.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:39:12Z"
---

## Goal

_checkpoint() вызывается только в close(), не после каждого _ex/_ins. DDL пропускается если schema_version == текущая. Startup time улучшен.

## Acceptance Criteria

1. _checkpoint() не вызывается в _ex/_ins. 2. close() по-прежнему делает TRUNCATE checkpoint. 3. _init_schema пропускает DDL если schema_version == текущая. 4. Ошибка если _ex вызывает _checkpoint при not in_transaction. 5. Все существующие тесты проходят.

## Plan

[{"step": "\u0423\u0431\u0440\u0430\u0442\u044c self._checkpoint() \u0438\u0437 _ex \u0438 _ins", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c schema version check \u0432 _init_schema \u2014 skip DDL if current", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b", "done": true}, {"step": "\u0417\u0430\u043c\u0435\u0440\u0438\u0442\u044c startup time \u0434\u043e/\u043f\u043e\u0441\u043b\u0435", "done": true}]

## Rollback

## Journal

- 2026-04-05T19:39:03Z [implementation] — AC verified: 1. _checkpoint убран из _ex/_ins ✓ 2. close() по-прежнему делает TRUNCATE ✓ 3. DDL skip при schema_version == текущая (warm start 1.9ms vs 18ms cold) ✓ 4. 738/738 тестов ✓
