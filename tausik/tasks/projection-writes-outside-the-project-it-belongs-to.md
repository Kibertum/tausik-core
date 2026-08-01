---
slug: projection-writes-outside-the-project-it-belongs-to
title: "Проекция уходит на каталог ВЫШЕ своей БД, а выключатель читается из cwd: голый backend пишет файлы в чужое место при каждом прогоне тестов"
status: planning
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: cascade-mutations-never-project-to-tree
scope: "scripts/state_triggers.py, tests/, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Найдено ревью сессии #154, ВОСПРОИЗВЕДЕНО мной живым прогоном. Два дефекта, у которых один корень, поэтому одна задача.

(1) АДРЕС. _BackendView.tausik_dir() возвращает dirname(abspath(db_path)), а _tree_root затем берёт dirname ОТ ЭТОГО и приписывает "tausik". Итог: dirname(dirname(db_path))/tausik. Это верно ТОЛЬКО когда БД лежит внутри .tausik/ под корнем проекта — инвариант, который шим унаследовал у ProjectService, не унаследовав того, что его обеспечивало.
ЗАМЕР: SQLiteBackend("<tmp>/case0/tausik.db"); be.epic_add("e","E"); be.epic_update("e", title="X") -> записан <tmp>/tausik/epics/e.md. То есть СОСЕДОМ каталога case0, а не внутри него. При db_path=":memory:" адрес уезжает в РОДИТЕЛЯ репозитория.

(2) ВЫКЛЮЧАТЕЛЬ. _auto_export_enabled() зовёт load_config() БЕЗ tausik_dir, а это, по документации project_config, «ambient project», то есть cwd процесса. При этом _tree_root тремя строками ниже специально ходит через svc.tausik_dir() и в докстринге НАЗЫВАЕТ причину: «keying on the cwd is the mcp-config-read-paths-ignore-project-handle defect». Путь починили, ПОЛИТИКУ — нет.
ЗАМЕР: из корня этого репозитория _auto_export_enabled() -> True (в .tausik/config.json стоит state.auto_export=true), и именно поэтому дефект (1) срабатывает в тестах: ни один тест не включал auto_export, их всех включил конфиг репозитория.

ПОСЛЕДСТВИЕ, наблюдаемое сейчас. Ревью прогнало `pytest tests/ -k "cascade or backend or task_update or projection or state_"` (305 тестов) и нашло 32 файла в ОБЩЕМ корне pytest basetemp: <basetemp>/tausik/epics/{e,e1,ep,epic-1,...}.md, stories/{s,st,mvp,setup,...}, tasks/... Все — ВНЕ tmp_path писавшего теста, в одном общем пространстве имён, с конфликтующими универсальными слагами (e, s, mvp, setup), и никогда не убираются. До появления auto_export_write тесты, строящие голый SQLiteBackend без ProjectService, не экспортировали вовсе. Гард conftest._guard_live_project_config сюда не достаёт — он про config.json — и его собственный докстринг называет исторический симптом ровно этого класса: «WinError 32 когда два набора идут разом, читается как флейк».

Внешние эффекты в третьем месте у объекта, чья вся суть — быть изолированным, это тот же класс, что чинил гард публикации в brain (decide на одноразовой БД создавал живую страницу в Notion). Здесь он вернулся на файловой системе.

## Acceptance Criteria

1. АДРЕС ВЫВОДИТСЯ ИЗ ДОКАЗАННОГО, А НЕ ИЗ ФОРМЫ ПУТИ. Запись из голого backend'а проецируется только тогда, когда БД действительно лежит в каталоге проекта (например, dirname(db_path) называется .tausik); в противном случае проекция НЕ ПРОИСХОДИТ ВОВСЕ — не «пишется куда-то ещё». Fail-closed, как у гарда публикации в brain: цена ложного отрицания — непроецированная строка, цена ложного положительного — файлы в чужом каталоге.
2. ВЫКЛЮЧАТЕЛЬ ЧИТАЕТСЯ ИЗ ТОЙ ЖЕ РУЧКИ, ЧТО И АДРЕС: _auto_export_enabled получает tausik_dir конкретного handle, а не ambient cwd. После фикса проект, выставивший state.auto_export=false, не получает дерево из-за того, что процесс стоит в другом репозитории, и наоборот.
3. ТЕСТ КРАСНЫЙ ДО ФИКСА, доказано прогоном: (а) голый SQLiteBackend вне .tausik/ не создаёт НИ ОДНОГО файла ни в своём каталоге, ни в родительском; (б) auto_export, выключенный в конфиге целевого проекта, не включается конфигом cwd. Обе проверки обязаны краснеть на текущем коде; вывод записан в журнал.
4. ЗАГРЯЗНЕНИЕ ИЗМЕРЕНО ДО И ПОСЛЕ. Прогон `pytest tests/ -k "cascade or backend or task_update or projection or state_"` с подсчётом *.md в корне pytest basetemp: до фикса число названо (ревью нашло 32), после фикса — ноль. Замер в журнале. Без него неизвестно, закрыт ли класс или только тот путь, который посмотрели.
5. НЕГАТИВ: настоящая проекция не сломана. Свойство tests/test_state_projection_tracks_db.py остаётся зелёным на всех сидах, tests/test_projection_follows_the_write.py и tests/test_projection_shrinks_with_the_db.py — тоже; каскадная запись из service_cascade через story_update/epic_update по-прежнему доходит до дерева. Фикс обязан отличать «БД проекта» от «любой БД», а не выключать хук.
6. ПРОВЕРКА ЗАПУСКОМ АРТЕФАКТА (память #346): реальная CLI-команда, меняющая эпик или стори, после фикса всё ещё обновляет tausik/ в ЭТОМ репозитории. Вывод в журнал.
7. Полный pytest зелёный; ruff и mypy чистые; bootstrap drift отсутствует.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert

## Journal
