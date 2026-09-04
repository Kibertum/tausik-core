---
slug: tools-spec-adds-a-possibly-nonexistent-dir-to-syspath
title: "tools_spec.py кладёт в sys.path каталог без проверки: мой замер в #210 был проведён НЕВЕРНО"
status: planning
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
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

ПРЕМИСА ИЗ ПЕРЕДАЧИ #209: «tools_spec.py кладёт в sys.path несуществующий каталог».
ЧТО ТОЧНО ЕСТЬ В КОДЕ (проверено в #210): harness/claude/mcp/project/tools_spec.py строки 20-22 — _SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts"), то есть ДВА уровня вверх от каталога модуля, и вставка в sys.path БЕЗ проверки существования.
ЧЕСТНО О МОЁМ ЗАМЕРЕ: я пытался это проверить и ПОСЧИТАЛ НЕВЕРНО — взял ТРИ уровня вверх вместо двух. Поэтому мой результат («в исходнике путь не существует») НИЧЕГО НЕ ДОКАЗЫВАЕТ, и премиса остаётся НЕПРОВЕРЕННОЙ. Записано здесь именно затем, чтобы преемник не принял мою ошибку за замер: неверный замер в журнале опаснее отсутствующего, потому что выглядит как основание.
ПЕРВЫЙ ШАГ: посчитать пути для ОБОИХ мест — исходника harness/claude/mcp/project/ и КАЖДОГО развёрнутого профиля (.claude, .cursor, .kilo, .opencode, .qwen) — и сказать, где каталог есть, а где нет.
ПОЧЕМУ ДЕФЕКТ ТАКОГО РОДА ЖИВЁТ ГОДАМИ: вставка несуществующего пути в sys.path НЕ ПАДАЕТ. Она молча ничего не даёт, импорт потом отрабатывает по другой причине — или не отрабатывает вовсе, и связь между причиной и симптомом уже потеряна. Отказ обязан быть громким там, где он происходит.
ВНЕ ОБЪЁМА 1.9: гигиена импорта в harness.

## Acceptance Criteria

## Plan

## Rollback

## Journal
