---
slug: record-direct-edit-is-a-dead-duplicate-of-the-live-path
title: "record_direct_edit — мёртвый дубликат живого пути записи обхода гейта: две реализации одних трёх строк, вызывается ни одна"
status: planning
epic: release-19-renar-conformance
story: evidence-is-substance-not-keywords
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/gate_bypass_record.py"
  - "scripts/project_cli_events.py"
  - "tests/test_direct_edit_bypass_record.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО АУДИТОМ SENAR 9.5 В СМЕНЕ #227, детектором недостижимого кода (severity HIGH). scripts/gate_bypass_record.py:133 определяет record_direct_edit(project_dir, task_slug, **fields) — обёртку, которая зовёт build() и emit_supervision_bypass(). Её не вызывает НИКТО: ни продуктовый код, ни тесты, ни MCP.

ПРОВЕРЕНО, ЧТО ЭТО НЕ ПОТЕРЯННЫЙ МЕХАНИЗМ. Живой путь записи §8.6(j) существует и работает — scripts/project_cli_events.py:79 импортирует DIRECT_EDIT_VECTOR, BypassRecordRefused и build, сам собирает details и сам зовёт emit_supervision_bypass. То есть запись обхода гейта происходит, метрика 8 наполняется, и первоначальное подозрение «механизм записи никогда не срабатывает» замером ОПРОВЕРГНУТО. Осталось ровно одно: дублирующая реализация тех же трёх шагов, к которой нет ни одного обращения.

ПОЧЕМУ ЭТО ВСЁ-ТАКИ ДЕФЕКТ, А НЕ БЕЗОБИДНЫЙ ХВОСТ. Два места, делающие одно и то же, расходятся при первой же правке одного из них: следующий, кто починит порядок полей или добавит обязательное поле в живом пути, не увидит мёртвого — и обёртка станет тихо неверной, оставаясь при этом публичным именем модуля, которое легко позвать. Дублирование правила записи регулируемого исключения (Gate Bypass 3.13) — не то место, где стоит держать вторую копию.

ЧТО ДЕЛАЕТСЯ: либо удалить record_direct_edit, либо сделать её ЕДИНСТВЕННЫМ путём и позвать из project_cli_events. Второе предпочтительнее по существу (одно правило — одно место), но требует проверить, что рефакторинг не ломает отказ BypassRecordRefused, который сегодня превращается в SystemExit(2) на стороне CLI. Решить сравнением, а не вкусом.

ПОЧЕМУ НЕ В 1.9: ни одно из двух обещаний релиза на этом не держится (решение #337).

## Acceptance Criteria

## Plan

## Rollback

git revert <commit>. Изменение затрагивает один модуль и его вызывающую сторону; данные и схема не трогаются. Если выбран вариант с удалением — откат возвращает функцию, если с объединением — возвращает обе реализации.

## Journal
