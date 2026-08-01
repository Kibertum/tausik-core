---
slug: projection-hook-claims-coverage-it-does-not-have
title: "Докстринг и CHANGELOG обещают «мутатор, о котором никто не помнит, покрыт», а хук стоит только на _update и трёх удалениях"
status: planning
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 55
defect_of: cascade-mutations-never-project-to-tree
scope: "scripts/state_triggers.py, scripts/project_backend.py, scripts/backend_crud.py, scripts/backend_crud_knowledge.py, tests/, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Найдено ревью сессии #154 — четырьмя ревьюерами независимо, с перечнем обходных путей. Дефект НЕ В КОДЕ: код делает ровно то, что делает. Дефект в УТВЕРЖДЕНИИ о нём, а это ровно «тихая ошибка», к которой в проекте нулевая толерантность, потому что следующий автор поверит обещанию.

ЧТО ОБЕЩАНО. scripts/state_triggers.py::auto_export_write: «this hook fires because a projected table was written, so a mutator nobody remembers is covered on the commit that introduces it. A list that has to be extended is a list that gets forgotten.» CHANGELOG.md повторяет дословно. tests/test_projection_follows_the_write.py в докстринге — тоже.

ЧТО ЕСТЬ. _project_write достижим ТОЛЬКО из _update() и трёх вызовов _delete_projected(). Мимо проходят:
- ВСЕ INSERT (_ins): epic_add, story_add, task_add, decision_add, memory_add. Проверено: голый backend с тремя add-ами не создал НИ ОДНОГО файла; файл появился только после epic_update.
- ВСЕ записи в memory и decisions: у этих таблиц нет метода, идущего через _update, memory_delete в backend_crud_knowledge.py:122 — сырой _ex. Две из пяти проецируемых сущностей не получают от хука ничего.
- task_set_call_budget / task_set_cost_budget / task_set_token_budget / task_set_*_actual (backend_crud.py:253-297) — сырые _ex, пишущие ПРОЕЦИРУЕМЫЕ колонки call_budget и tier. Замер: БД 55, файл call_budget: null.
- task_append_notes и task_claim (project_backend.py:434,444) — сырые _ex.
- backend_graph.py:69 UPDATE memory SET archived_at — массовая архивация.

ПОЧЕМУ ПРОД НЕ ЛОМАЕТСЯ: ~20 ручных вызовов auto_export_* на сервисном слое ОСТАВЛЕНЫ. То есть механизмов проекции теперь ДВА, и каждый читается как гарантия. Это ХУЖЕ одного неполного списка: следующий автор решит, что хук покрывает его, и снимет ручной вызов.

СВЯЗАННОЕ, решать здесь же (M6 ревью): там, где работают ОБА слоя, одна операция рендерит файл дважды. Замер: task_start -> три вызова export_one (tasks/t1, stories/s1, tasks/t1), task_block и task_plan -> по два на один слаг. Пока хук неполон, снимать ручные вызовы НЕЛЬЗЯ — поэтому решение про дубль зависит от решения про полноту и принимается вместе с ним.

## Acceptance Criteria

1. ВЫБРАН И ЗАПИСАН РЕШЕНИЕМ один из двух исходов, а не смесь. (а) ХУК ДОВОДИТСЯ ДО ОБЕЩАННОГО: перехват спускается на _ins и на сырые _ex по проецируемым таблицам (или соответствующие методы переводятся на _update), после чего ручные вызовы сервисного слоя снимаются как избыточные. (б) ОБЕЩАНИЕ ПРИВОДИТСЯ К ПРАВДЕ: докстринг, оба CHANGELOG и докстринг test_projection_follows_the_write.py говорят ровно то, что покрыто — UPDATE по слагу и три удаления по epics/stories/tasks, — и ЯВНО называют то, что не покрыто, вместе с причиной, почему ручные вызовы остаются документированным механизмом.
2. ЛЮБОЙ ИЗ ИСХОДОВ ОСТАВЛЯЕТ ОДИН ЧИТАЕМЫЙ ОТВЕТ НА ВОПРОС «покрыт ли мой новый мутатор». Сегодня их два и они противоречат друг другу. Проверяется чтением: в коде не должно остаться места, где ручной вызов и хук оба выглядят как гарантия без указания, кто из них главный.
3. ПЕРЕЧЕНЬ ОБХОДНЫХ ПУТЕЙ ЗАКРЫТ ИЛИ НАЗВАН ПОИМЕННО. Все пункты из цели (INSERT'ы; memory и decisions целиком; task_set_* бюджеты и actual'ы; task_append_notes; task_claim; массовая архивация в backend_graph) либо покрыты, либо перечислены в докстринге как непокрытые. Молчаливого умолчания не остаётся ни по одному.
4. ТЕСТ ЗАКРЕПЛЯЕТ ВЫБРАННЫЙ ИСХОД И КРАСНЕЕТ ПРИ ВОЗВРАТЕ. Для (а) — расширение храповика путей записи в tests/test_state_projection_tracks_db.py так, чтобы INSERT'ы и записи в memory/decisions считались покрытыми ХУКОМ, а не сервисным слоем: проверяется отключением ручных вызовов, при котором свойство обязано остаться зелёным. Для (б) — тест, доказывающий, что ручной вызов НЕОБХОДИМ (снятие его роняет свойство), чтобы обещание и код нельзя было развести снова.
5. ДУБЛИРУЮЩАЯ ПРОЕКЦИЯ: измерена до и после (сегодня task_start -> 3 вызова export_one, task_block и task_plan -> по 2). Если дубль остаётся, в журнале сказано, почему он приемлем; если снимается — свойство проекции зелёное на всех сидах после снятия.
6. НЕГАТИВ: покрытие не сужено. tests/test_state_projection_tracks_db.py, test_projection_follows_the_write.py и test_projection_shrinks_with_the_db.py зелёные; каскад из service_cascade по-прежнему доходит до дерева.
7. Полный pytest зелёный; ruff и mypy чистые; bootstrap drift отсутствует.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены — включая ИСПРАВЛЕНИЕ прежней записи, если выбран исход (б): запись, обещающая непокрытое, остаётся ложной, пока её не переписали.

## Plan

## Rollback

git revert

## Journal

- 2026-08-01T18:44:24Z [planning] — ИНВЕНТАРЬ, собран заранее в сессии #155 (пока задача не начата). МЕСТА, ПОВТОРЯЮЩИЕ ОБЕЩАНИЕ (все обязаны стать правдой или измениться): - scripts/state_triggers.py:253 — «a mutator nobody remembers is covered on the commit that introduces it» - CHANGELOG.md:218 — дословно то же - tests/test_projection_follows_the_write.py:11 — дословно то же - CHANGELOG.ru.md:16 — ВНИМАНИЕ: это запись сессии #155 про адрес проекции, написанная МНОЙ СЕГОДНЯ, и она открывается словами «Подвесив git-проекцию к слою записи, мы накрыли ею мутаторы, о которых никто не помнит». То есть ложное обещание протянуто в НОВЫЙ текст. Правится здесь же. Зеркала в docs/ нет — grep по docs/ пуст. ЧИСЛА: - ручных вызовов auto_export_entity / auto_export_by_id на сервисном слое: 18, в четырёх модулях — service_decide.py, service_hierarchy.py, service_knowledge.py, service_task.py. - сырые UPDATE по проецируемым таблицам мимо _update: backend_crud.py:263 (call_budget+tier), :273 (call_actual), :283 (f-строка по колонке), backend_graph.py:70 (массовая архивация memory). Плюс UPDATE sessions SET handoff (backend_crud.py:179) — sessions НЕ проецируется, к делу не относится. - _project_write (project_backend.py:160) отложен при открытой транзакции и сбрасывается в _flush_pending_projection с дедупликацией dict.fromkeys — значит дубль внутри ОДНОЙ транзакции уже снят; замеренный дубль task_start -> 3 вызова идёт от смеси «ручной вызов + хук», а не от самого хука.
- 2026-08-01T18:45:49Z [planning] — AC5, замер дубля ДО решения (мой прогон, шпион поверх state_export.export_one, изолированный проект во временном каталоге с .tausik/config.json state.auto_export=true). task_block: 2 вызова export_one -> [('tasks','t1'), ('tasks','t1')] task_plan: 2 вызова export_one -> [('tasks','t1'), ('tasks','t1')] task_start: замерить не удалось — QG-0 Start Gate отказал на тестовом AC («no negative scenario»), проба не дошла до операции. Число 3 из ревью #154 НЕ ПОДТВЕРЖДЕНО МОИМ ПРОГОНОМ и должно быть перезамерено внутри задачи с валидным AC, а не взято на веру. ЧТО ЭТО ЗНАЧИТ. Дубль идёт от СМЕСИ двух механизмов (ручной вызов на сервисном слое + хук на _update), а не от хука самого по себе: внутри одной транзакции _flush_pending_projection уже дедуплицирует через dict.fromkeys. Цена дубля — вторая сериализация плюс чтение файла, но НЕ вторая запись: auto_export_entity идемпотентен, при совпадении содержимого возвращает False без записи. То есть дубль стоит CPU и I/O на чтение, а не mtime-шум в дереве. Это делает исход (б) существенно дешевле, чем кажется по слову «дубль».
