---
slug: v2-projection-hook-covers-every-write
title: "[2.0] Перехват проекции покрывает КАЖДУЮ запись, а не UPDATE по слагу: снять ручной слой и сделать обещание кодом"
status: planning
epic: arch-debt-post-18
story: adp18-projection-coverage
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 150
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

Вынесено решением #216 из projection-hook-claims-coverage-it-does-not-have. В 1.8 выбран исход (б) — обещание приведено к правде; здесь делается исход (а) — правдой становится КОД.

СЕГОДНЯШНЕЕ СОСТОЯНИЕ (замерено в сессии #155, не оценка): auto_export_write достаёт только _update по слагу и три _delete_projected по epics/stories/tasks. Проекцию всего остального держат 18 ручных вызовов auto_export_entity / auto_export_by_id в четырёх модулях (service_task, service_hierarchy, service_knowledge, service_decide). Проба: заглушить ТОЛЬКО ручный слой (различитель — хук передаёт _BackendView, ручной слой настоящий ProjectService), оставив хук живым, -> 11 failed / 3 passed, свойство красное на всех шести сидах. Закреплено тестом test_the_hook_alone_does_not_carry_the_projection, который ОБЯЗАН покраснеть, когда эта задача будет сделана.

ЧТО ИМЕННО ПРИДЁТСЯ СДЕЛАТЬ (перечень непокрытого — из докстринга auto_export_write):
1. INSERT'ы. project_backend._ins принимает СЫРОЙ SQL и не знает ни таблицы, ни слага — поэтому «повесить хук на _ins» невозможно без разбора SQL. Нужно дать _ins таблицу и ключ в каждой точке вызова (epic_add, story_add, task_add, decision_add, memory_add) либо ввести _ins_projected по аналогии с _delete_projected.
2. memory и decisions целиком: их файлы ключуются по id строки, а не по колонке слага, поэтому хуку нужен путь по id (сегодня это отдельная функция auto_export_by_id). memory_delete в backend_crud_knowledge.py — сырой _ex.
3. Сырые _ex по проецируемым колонкам: backend_crud.py:263 (call_budget+tier), :273 (call_actual), :283 (колонка через f-строку), task_append_notes и task_claim в project_backend.py. Перевести на _update либо накрыть отдельно.
4. Массовая архивация backend_graph.py:70 (UPDATE memory SET archived_at по множеству строк): слаги/id придётся доставать SELECT'ом ДО апдейта, иначе проецировать нечего.
5. После этого — снять 18 ручных вызовов и убедиться, что дубль рендера ушёл (сегодня task_block и task_plan дают по 2 вызова export_one на слаг; task_start ревью насчитало 3, моим прогоном НЕ подтверждено, перезамерить).

ПОЧЕМУ НЕ В 1.8: это переработка слоя записи накануне тега. Цена ошибки в _ins/_ex — не непроецированный файл, а испорченная запись в БД.

## Acceptance Criteria

1. ПЕРЕХВАТ ПОКРЫВАЕТ ПЕРЕЧЕНЬ ЦЕЛИКОМ. Все пять пунктов цели (INSERT'ы; memory и decisions; сырые _ex по бюджетам, task_append_notes, task_claim; массовая архивация) идут через слой записи. В докстринге auto_export_write не остаётся ни одного пункта в разделе «что НЕ покрыто» — либо остаётся с указанием, почему он неустраним.
2. ДОКАЗАНО СНЯТИЕМ, А НЕ ЧТЕНИЕМ. tests/test_state_projection_tracks_db.py::test_the_hook_alone_does_not_carry_the_projection ОБЯЗАН покраснеть: заглушение ручного слоя больше не роняет свойство. Тест УДАЛЯЕТСЯ, а не правится под новый исход, и вместо него ставится обратный — свойство зелёное при полностью снятом ручном слое, на всех шести сидах.
3. РУЧНЫЕ ВЫЗОВЫ СНЯТЫ. 18 вызовов auto_export_entity / auto_export_by_id в service_task, service_hierarchy, service_knowledge, service_decide удалены. Проверяется grep'ом: вне state_triggers.py вызовов не остаётся.
4. ДУБЛЬ ИЗМЕРЕН ДО И ПОСЛЕ. Замер шпионом поверх state_export.export_one: сегодня task_block=2, task_plan=2 на слаг, task_start перезамерить (число 3 из ревью #154 не подтверждено). После — по одному на слаг на операцию. Числа в журнале.
5. НЕГАТИВ, ЦЕНА ОШИБКИ НАЗВАНА. Задача трогает _ins и _ex, то есть ОБЫЧНЫЙ путь записи в БД: ни одна правка не должна менять то, что попадает в SQLite. Проверяется тем, что весь набор тестов записи (не только проекционные) зелёный, и тем, что проекция остаётся FAIL-OPEN — отказ сериализации по-прежнему не откатывает запись (test_export_failure_does_not_roll_back_the_write).
6. ПРОЗА ДОГНАЛА КОД. Докстринг auto_export_write, докстринг tests/test_projection_follows_the_write.py и записи в обоих CHANGELOG (включая ОТЗЫВ, поставленный сессией #155) переписаны на то, что стало правдой. Ни одно место не остаётся с отозванной формулировкой.
7. Полный pytest зелёный; ruff и mypy чистые; bootstrap drift отсутствует.

## Plan

## Rollback

## Journal
