---
slug: projection-writes-outside-the-project-it-belongs-to
title: "Проекция уходит на каталог ВЫШЕ своей БД, а выключатель читается из cwd: голый backend пишет файлы в чужое место при каждом прогоне тестов"
status: done
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
relevant_files:
  - "scripts/state_triggers.py"
  - "tests/test_projection_stays_in_its_project.py"
  - "tests/test_state_triggers.py"
  - "tests/test_state_projection_tracks_db.py"
  - "tests/test_projection_follows_the_write.py"
  - "tests/test_projection_shrinks_with_the_db.py"
  - "tests/test_state_roundtrip_gate.py"
  - "tests/test_task_update_writes_all_or_nothing.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-01T18:52:41Z"
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

- 2026-08-01T18:21:30Z [implementation] — AC4, замер ДО фикса. Прогон `pytest tests/ -k "cascade or backend or task_update or projection or state_" --basetemp=<bt>` = 311 passed. Подсчёт *.md: 642 всего, из них 31 лежит в <bt>/tausik/{epics,stories,tasks,decisions} — то есть в ОБЩЕМ корне basetemp, вне каталога любого теста. Ревью насчитало 32; расхождение на единицу — разница выборки, класс тот же. Слаги конфликтующие и универсальные: e, e1, ep, epic-1, s, st, mvp, setup, t1, t2, x. Цель после фикса: ноль.
- 2026-08-01T18:25:55Z [implementation] — AC6: проверка запуском артефакта — эта строка обязана доехать до tausik/ через развёрнутую копию .claude/scripts, а не через исходник.
- 2026-08-01T18:40:14Z [implementation] — AC3, проба красноты ПОТЕСТОВО (память #360, а не «набор покраснел»). До фикса: 4 failed, 1 passed. Красные — test_bare_backend_outside_a_project_writes_no_file_anywhere, test_in_memory_db_projects_nowhere, test_target_off_while_cwd_is_on_stays_off, test_target_on_while_cwd_is_off_still_projects. Зелёный — test_backend_inside_a_project_still_projects (позитивный контроль, обязан быть зелёным ДО и ПОСЛЕ). ВАЖНО: test_in_memory_db_projects_nowhere СНАЧАЛА ПРОШЁЛ ЛОЖНО. Причина ровно та, которую чиню: старый адрес — РОДИТЕЛЬ каталога процесса, а assert смотрел внутрь tmp_path, стоя в tmp_path. Файл ложился ВЫШЕ проверки. Переписал: cwd — подкаталог tmp_path, дефект больше не выходит за область наблюдения. Проба, из которой дефект может уйти, не доказывает ничего. AC4, замер ПОСЛЕ фикса: тот же прогон -k "cascade or backend or task_update or projection or state_" = 316 passed (311 старых + 5 новых), файлов *.md в ОБЩЕМ корне basetemp — 0 (было 31). AC6, запуском артефакта: `.tausik/tausik task log <этот slug>` через развёрнутую копию .claude/scripts после bootstrap --ide all. sha1 tausik/tasks/<slug>.md 852857446a0d -> 657cf9584fea, строка журнала в файле. Настоящая проекция жива.
- 2026-08-01T18:52:38Z [implementation] — AC verified: 1. ✓ АДРЕС ВЫВОДИТСЯ ИЗ ДОКАЗАННОГО. scripts/state_triggers.py::_tree_root теперь требует, чтобы каталог НАЗВАЛ СЕБЯ: basename(tausik_dir) != project_config.TAUSIK_DIR -> None, проекции нет вовсе. Fail-closed, как гард публикации brain. Проверено tests/test_projection_stays_in_its_project.py::TestTheAddressIsProven::test_bare_backend_outside_a_project_writes_no_file_anywhere и ::test_in_memory_db_projects_nowhere. 2. ✓ ВЫКЛЮЧАТЕЛЬ ИЗ ТОЙ ЖЕ РУЧКИ. _auto_export_enabled(tausik_dir) — аргумент ОБЯЗАТЕЛЬНЫЙ, без умолчания на ambient-проект, поэтому возврат к load_config() без аргумента невозможен молча. Аргумент ВЫВОДИТСЯ ИЗ УЖЕ РАЗРЕШЁННОГО АДРЕСА (сосед root по имени .tausik), а не разрешается второй раз: «куда пишем» и «можно ли писать» структурно не способны назвать разные проекты. Обе стороны проверены: ::test_target_off_while_cwd_is_on_stays_off и ::test_target_on_while_cwd_is_off_still_projects. 3. ✓ ТЕСТ КРАСНЫЙ ДО ФИКСА, проба ПОТЕСТОВАЯ (память #360). До: 4 failed, 1 passed — красные ровно четыре пробы дефекта, зелёный только позитивный контроль test_backend_inside_a_project_still_projects. ОТДЕЛЬНО: test_in_memory_db_projects_nowhere СНАЧАЛА ПРОШЁЛ ЛОЖНО — старый адрес есть РОДИТЕЛЬ каталога процесса, и файл ложился выше области, куда смотрел assert; тест переписан (cwd — подкаталог tmp_path), после чего покраснел. Проба, из которой дефект может уйти, не доказывает ничего. 4. ✓ ЗАГРЯЗНЕНИЕ ИЗМЕРЕНО ДО И ПОСЛЕ. Прогон `pytest tests/ -k "cascade or backend or task_update or projection or state_" --basetemp=<bt>`: ДО — 311 passed, 31 файл *.md в ОБЩЕМ корне <bt>/tausik (ревью называло 32; расхождение на единицу — разница выборки). ПОСЛЕ — 316 passed (311 + 5 новых), 0 файлов. Оба замера в журнале задачи. 5. ✓ НАСТОЯЩАЯ ПРОЕКЦИЯ НЕ СЛОМАНА. tests/test_state_projection_tracks_db.py (свойство на всех сидах), test_projection_follows_the_write.py, test_projection_shrinks_with_the_db.py, test_state_triggers.py, test_state_roundtrip_gate.py, test_task_update_writes_all_or_nothing.py — зелёные в scoped verify (15 файлов) и в полном прогоне. Каскад service_cascade доходит до дерева. Заглушки монкейпатча получили ОБЯЗАТЕЛЬНЫЙ позиционный аргумент (lambda _d:), а не *_a: возврат к вызову без ручки снова покраснеет. 6. ✓ ПРОВЕРКА ЗАПУСКОМ АРТЕФАКТА (память #346). После bootstrap --ide all: `.tausik/tausik task log <этот slug>` через развёрнутую копию .claude/scripts. sha1 файла tausik/tasks/<slug>.md 852857446a0d -> 657cf9584fea, строка журнала в проекции. Реальный CLI по-прежнему обновляет tausik/ в ЭТОМ репозитории. 7. ✓ ПОЛНЫЙ PYTEST ЗЕЛЁНЫЙ: 6549 passed, 24 skipped, 0 failed, 0 errors (642s). ruff check — All checks passed. mypy — Success: no issues found in 294 source files. bootstrap --ide all прогнан, drift отсутствует (verify passed). ruff format для десяти затронутых файлов — «already formatted». 8. ✓ CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md — прозаическая запись «the projection writes into the project that owns the database, or nowhere» / «проекция пишет в тот проект, которому принадлежит база, либо не пишет вовсе», с обоими дефектами, замером 31 -> 0 и объяснением, почему выбран fail-closed. ПОБОЧНО (вне области задачи, оформлено отдельно): (а) заведена задача ruff-format-is-not-gated-and-86-files-diverged — `ruff format --check` не подключён НИ К ОДНОМУ гейту (реестр объявляет только `ruff check {files}`), 86 файлов разошлись, проверено на ЧИСТОМ дереве до моих правок; (б) ERROR «тест мутировал живой config.json» в первом фоновом прогоне оказался МОИМ артефактом — bootstrap писал конфиг параллельно прогону; в изоляции test_skill_manager.py 76 passed и sha конфига не меняется, дефект НЕ заведён; (в) tests/test_projection_stays_in_its_project.py объявил CROSSCUTTING_SCOPE (а не отказ от него): эвристика по имени файла не связала бы его с state_triggers.py, и гейт test_crosscutting_registry.py это поймал.
- 2026-08-01T18:53:00Z [done] — Root cause (logic-error): адрес проекции вычислялся ФОРМОЙ ПУТИ — dirname(dirname(db_path))/tausik, — а это корень проекта только при инварианте «база лежит в .tausik/ под корнем». Инвариант обеспечивал ProjectService; когда хук спустили на голый SQLiteBackend, он доехал туда допущением, а не величиной, и адрес стал указывать на каталог-соседа. Второй половиной того же корня был выключатель: он разрешал проект ЗАНОВО и через cwd, поэтому конфиг одного проекта отвечал за базу другого. Prevention: величина, определяющая внешний эффект, обязана быть выведена из ДОКАЗАННОГО признака (каталог называет себя .tausik), а не из формы строки; и там, где решение состоит из пары «куда» и «можно ли», вторая половина ВЫВОДИТСЯ ИЗ ПЕРВОЙ, а не разрешается независимо — иначе их можно развести. Аргумент, который нельзя опустить (обязательный позиционный вместо умолчания), делает возврат к ambient-разрешению невозможным молча. Domain: результат осмыслен вне тестов и проверен на живой системе. Реальный CLI `.tausik/tausik task log` через развёрнутую копию .claude/scripts после bootstrap продолжает обновлять tausik/ в этом репозитории (sha1 файла задачи изменился, строка журнала на месте) — то есть проекция настоящего проекта, у которого база лежит в .tausik/, работает как прежде. И симметрично: прогон 311 тестов, каждый из которых строит временную базу ВНЕ .tausik/, перестал оставлять 31 посторонний файл в общем каталоге. Обе стороны — не «тест позеленел», а наблюдаемое поведение файловой системы до и после.
