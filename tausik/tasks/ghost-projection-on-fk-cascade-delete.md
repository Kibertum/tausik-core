---
slug: ghost-projection-on-fk-cascade-delete
title: "Удаление эпика/стори каскадит в БД по внешнему ключу, а файлы детей остаются в дереве: проекция описывает строки, которых нет"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 70
defect_of: state-export-trigger-misses-task-linked-decisions
scope: "scripts/project_backend.py (epic_delete, story_delete, task_delete и общий помощник, снимающий проекции строк, удалённых движком по внешнему ключу), scripts/state_triggers.py при необходимости, tests/, CHANGELOG.md, CHANGELOG.ru.md. После правки scripts/ обязателен bootstrap --ide all."
scope_exclude: "НЕ трогать статусный каскад (закрыт задачей cascade-mutations-never-project-to-tree) и частичную запись в task_update (task-update-partial-write-then-raise). НЕ переписывать property-тест под новые сценарии — это projection-property-test-cannot-reach-cascades. Отказ от ON DELETE CASCADE в схеме допустим ТОЛЬКО с миграцией и явной записью в журнале о принятой цене отката; по умолчанию схема не меняется."
relevant_files:
  - ".gitattributes"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "scripts/project_backend.py"
  - "scripts/state_triggers.py"
  - "tausik/stories/kb-git-sync.md"
  - "tausik/tasks/kb-brain-deprecate.md"
  - "tausik/tasks/kb-export-tasks.md"
  - "tausik/tasks/revise-kb-export-tasks-superseded.md"
  - "tests/test_state_triggers.py"
  - "tausik/decisions/koeffitsient-kalibrovki-na-okne-n-10-neprigoden-dlya.md"
  - "tausik/decisions/reviziya-obema-1-8-sokratila-byudzhet-s-2087-do-1927-no-ne.md"
  - "tausik/decisions/revyu-pyati-zakrytyh-zadach-nashlo-chto-state-export.md"
  - "tausik/memory/audit-kachestva-sessii-153-revyu-partii-152-nashlo-devyat.md"
  - "tausik/memory/novoe-proizvodnoe-derevo-obyazano-byt-vneseno-v-kazhdyy.md"
  - "tausik/memory/otnoshenie-kotorym-vladeet-dvizhok-bd-kaskad-po-vneshnemu.md"
  - "tausik/memory/zadacha-obyavivshaya-svoyu-zhe-proektsiyu-v-relevant-files.md"
  - "tausik/tasks/brain-db-binding-ignores-path-case.md"
  - "tausik/tasks/cascade-mutations-never-project-to-tree.md"
  - "tausik/tasks/complexity-proxy-counts-state-projection.md"
  - "tausik/tasks/docs-drift-after-s152-batch.md"
  - "tausik/tasks/ghost-projection-on-fk-cascade-delete.md"
  - "tausik/tasks/projection-property-test-cannot-reach-cascades.md"
  - "tausik/tasks/publish-risk-gate-docstring-lies-after-205.md"
  - "tausik/tasks/risk-l3-still-blocks-after-demotion.md"
  - "tausik/tasks/service-knowledge-one-line-from-filesize-gate.md"
  - "tausik/tasks/task-update-partial-write-then-raise.md"
  - "tausik/tasks/tausik-tree-gitattributes-lf.md"
  - "tausik/tasks/tool-call-syntax-leaks-into-entity-text.md"
  - "tests/test_projection_follows_the_write.py"
  - "tests/test_projection_shrinks_with_the_db.py"
  - "tests/test_state_tree_eol_pin.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-28T21:39:47Z"
---

## Goal

Найдено ревью сессии #153 (договорённость владельца о ревью каждые 5 закрытых задач). ВОСПРОИЗВЕДЕНО ДВУМЯ НЕЗАВИСИМЫМИ АГЕНТАМИ на живом коде против временной БД, не чтением.

ВОСПРОИЗВЕДЕНИЕ: epic_add('e1') -> story_add('e1','s1') -> task_add('s1','t1'), все три спроецированы; затем epic_delete('e1'). В БД пропадают и story, и task. На диске исчезает только tausik/epics/e1.md; tausik/stories/s1.md и tausik/tasks/t1.md ОСТАЮТСЯ. То же самое для одиночного story_delete('s1') — task t1 уходит из БД, файл остаётся. build_tree(db) возвращает пустой список, дерево на диске — два файла.

ПРИЧИНА. scripts/backend_schema.py:25,36 объявляют stories.epic_id и tasks.story_id как ON DELETE CASCADE, а каждое соединение работает с PRAGMA foreign_keys=ON (scripts/project_backend.py:89). Значит детей удаляет САМ SQLite, и питон об этом не узнаёт. service_hierarchy.epic_delete:61-65 и story_delete:89-93 вызывают _project только для удаляемой сущности, потому что список удалённых строк им никто не сообщает.

ПОЧЕМУ ЭТО КРИТИЧНО. Это ровно тот класс «GHOST — файл, описывающий строку, которой в БД больше нет», который докстринг state_triggers.py объявляет устранённым, а задача state-export-trigger-misses-task-linked-decisions закрывала под формулировкой «проекция следует за любой мутацией». Инвариант коммита ff0fc86 — «build_tree(db) равен дереву на диске после ЛЮБОЙ последовательности мутаций» — на этом входе ложен. Дерево tausik/ коммитится, то есть призраки уезжают в git и тиммейт видит задачи, которых нет.

ТРЕТИЙ ЛЕЙК ОДНОГО КОРНЯ, вместе с cascade-mutations-never-project-to-tree (статусный каскад) и task-update-partial-write-then-raise. НО ЧИНИТСЯ ОТДЕЛЬНО: единый перехват на уровне записи в БД (см. предложение по SQLiteBackend._update в задаче про статусный каскад) эту дыру НЕ закроет — удаление выполняет движок SQLite, а не питоновский код. Варианты, которые надо взвесить в задаче: перечислять детей ДО удаления и убирать их проекции явно, либо отказаться от ON DELETE CASCADE в пользу прикладного каскада, либо сверять дерево с build_tree после удаления. Выбор обосновать, а не взять первый.

## Acceptance Criteria

1. Удаление родителя убирает проекции ВСЕХ детей: после epic_add -> story_add -> task_add -> epic_delete на диске не остаётся ни tausik/stories/<slug>.md, ни tausik/tasks/<slug>.md. Тест воспроизводит именно эту последовательность и падает до фикса.
2. То же для одиночного story_delete: удаление стори с задачей внутри убирает и файл задачи.
3. Механизм выбран ЯВНО и обоснован в журнале одним из трёх: перечисление детей до удаления, отказ от ON DELETE CASCADE в пользу прикладного каскада, сверка дерева с build_tree после удаления. Названо, почему отвергнуты два других — в частности, почему не годится перехват на уровне записи (удаление выполняет движок SQLite, питон о нём не узнаёт).
4. Гарантия дана СВОЙСТВОМ, а не перечнем двух методов (конвенция #354): после удаления любой сущности дерево на диске равно build_tree(db). Проверка снимается после удаления, а не в конце последовательности, иначе она не отличит «убрали» от «никогда не создавали».
5. НЕГАТИВ И ГРАНИЦЫ. (а) Удаление НЕ трогает файлы посторонних сущностей: соседний эпик со своими детьми остаётся в дереве целиком. (б) Повторное удаление уже удалённого не падает и не удаляет лишнего. (в) Ошибка удаления файла не откатывает запись в БД и не бросает наружу — контракт fail-open (state_triggers.py:18-20) сохранён; тест доказывает, что при недоступном файле удаление сущности всё равно проходит.
6. Полный pytest зелёный; ruff и mypy чистые; `tausik state export --check` зелёный.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert коммита. Изменения локализованы в слое удаления (service_hierarchy и/или backend) плюс тесты. Если выбран вариант с отказом от ON DELETE CASCADE — потребуется миграция схемы, и тогда откат идёт миграцией вниз; этот вариант выбирать только при явной записи в журнале, что цена отката принята.

## Journal

- 2026-07-28T21:29:06Z [implementation] — РЕАЛИЗАЦИЯ И ВЫБОР МЕХАНИЗМА (критерий 3). ВЫБРАНО: перечисление потомков ДО удаления, транзитивно, с последующим переспросом проекции для каждого. scripts/project_backend.py — три метода: _dependent_tables, _projection_victims, _delete_projected. epic_delete/story_delete/task_delete переведены на последний. ПОЧЕМУ НЕ ПЕРЕХВАТ НА УРОВНЕ ЗАПИСИ (тот, что закрыл статусный каскад). Удаление детей выполняет ДВИЖОК SQLite при foreign_keys=ON; питоновский код о нём не узнаёт вовсе, поэтому хук в _update по построению не может сработать — нечему срабатывать. ПОЧЕМУ НЕ ОТКАЗ ОТ ON DELETE CASCADE. Потребовал бы миграцию схемы, то есть откат через миграцию вниз вместо git revert, и перенёс бы целостность из движка в прикладной код — цена несопоставима с дефектом проекции. В scope_exclude этот вариант был допущен только с явной записью о принятой цене; цена не принята. ПОЧЕМУ НЕ СВЕРКА ДЕРЕВА С build_tree ПОСЛЕ УДАЛЕНИЯ. Это полная пересборка дерева (2110 файлов на этом проекте) ради удаления одной строки, то есть возврат к «периодическому полному экспорту», который и прятал дефект. ГЛАВНОЕ В ВЫБРАННОМ ВАРИАНТЕ — не перечисление, а ОТКУДА оно берётся. Состав детей читается из схемы через PRAGMA foreign_key_list по таблицам реестра ENTITY_DIRS, а не выписан в коде. Обе предыдущие починки в этой области привозили перечень (сначала два метода, потом шесть), и в каждом не хватало ровно того, что ломалось следующим. Здесь проецируемый вид с каскадным внешним ключом покрывается той миграцией, которая его вводит. ПОБОЧНО ЗАКРЫТА ТИХАЯ ПОЛОВИНА, которой не было в постановке: decisions.task_slug объявлен ON DELETE SET NULL, поэтому удаление задачи не удаляло решение, а МЕНЯЛО его — и файл решения продолжал называть несуществующую задачу. Тот же сбор потомков ловит и этот случай (в _dependent_tables принимаются и CASCADE, и SET NULL), а разделяет их export_one: None для исчезнувшей строки, свежие байты для изменившейся. Один механизм, два исхода, без ветвления по типу внешнего ключа. Самоссылающийся внешний ключ tasks.defect_of -> tasks(slug) обрабатывается тем же обходом; зацикливание исключено множеством seen, инициализированным самой удаляемой парой.
- 2026-07-28T21:29:30Z [implementation] — AC-1: ✓ tests/test_projection_shrinks_with_the_db.py::TestTheTreeShrinksWithTheDb::test_deleting_an_epic_takes_its_stories_and_tasks_off_disk — последовательность epic_add -> story_add -> task_add -> epic_delete; после удаления на диске пусто. AC-2: ✓ tests/test_projection_shrinks_with_the_db.py::TestTheTreeShrinksWithTheDb::test_deleting_a_story_takes_its_tasks_off_disk. AC-3: ✓ Механизм выбран явно, три варианта разобраны в журнале выше с причинами отказа от двух. AC-4: ✓ Проверка снимается как РАВЕНСТВО МНОЖЕСТВ дерева на диске и build_tree(db) сразу после удаления, а не как отсутствие конкретных файлов: ::test_deleting_a_story_takes_its_tasks_off_disk и ::test_a_set_null_child_is_re_rendered_not_removed сравнивают _on_disk(root) == _in_db(svc). Отличие «убрали» от «никогда не создавали» держится ПРЕМИСОЙ в первом тесте: до удаления все три файла обязаны быть на диске. Происхождение состава детей закреплено отдельно: ::TestVictimsComeFromTheSchema::test_children_are_discovered_not_listed, ::test_collection_is_transitive_and_terminates (внук собран, самоссылающийся ключ не зациклился, дублей нет). AC-5 (негатив): ✓ (а) посторонние сущности не трогаются — равенство множеств в ::test_deleting_a_story_takes_its_tasks_off_disk оставляет epics/ep.md на месте; (б) удаление, не совпавшее ни с чем, не трогает файлов — ::TestItStaysBestEffort::test_a_delete_that_matched_nothing_touches_no_files, повторное удаление возвращает 0; (в) ошибка проекции не срывает удаление — ::test_a_failing_export_does_not_break_the_delete, epic_delete возвращает 1 и строка в БД исчезает при падающем export_one. Границы реестра: ::test_an_unprojected_or_missing_parent_collects_nothing. ФАЛЬСИФИЦИРУЕМОСТЬ ПРОВЕРЕНА ПРОГОНОМ: сбор потомков временно заменён пустым списком, прогон дал 3 failed / 5 passed — упали ровно три различающих теста, включая SET NULL. После восстановления 8 passed. Тесты происхождения из схемы и best-effort остались зелёными и в сломанном состоянии: они охраняют, а не различают. Прогон линтеров после правки scripts/: ruff All checks passed, mypy Success 314 файлов, bootstrap --ide all выполнен. project_backend.py — 458 строк, лимит 500. Domain: осмысленность вне тестов. Дефект воспроизведён двумя независимыми агентами ревью на живом коде против временной БД до того, как был написан хоть один тест — сценарий взят из их воспроизведения дословно. Практический смысл проверяется тем, ЧТО именно оставалось на диске: не служебный мусор, а карточки задач с целями и критериями приёмки, то есть тиммейт после git pull видел бы в дереве работу, которой в проекте нет.
- 2026-07-28T21:40:08Z [done] — AC-6: ✓ (в нумерации парсера это критерий CHANGELOG, шестой позиционно). Парные записи «Исправлено — удаление родителя больше не оставляет детей на диске» добавлены в CHANGELOG.md и CHANGELOG.ru.md в шапку [Unreleased]; факт добавления подтверждён гейтом changelog при закрытии, а не самоотчётом. Пятый критерий карточки (полный прогон) закрыт цифрами: pytest 6510 passed / 24 skipped / 0 failed за 632.78s — прибавка ровно 8, столько же, сколько новых тестов; ruff All checks passed; mypy Success 314 файлов; `tausik state export --check` OK на 2111 файлах. Root cause (integration-mismatch): целостность данных отдана движку (ON DELETE CASCADE плюс PRAGMA foreign_keys=ON), а производное представление — прикладному коду, и между двумя корректными по отдельности механизмами не было связи. SQLite удалял детей молча: ни исключения, ни возвращаемого значения, ни события, поэтому снятие проекции в этой точке не срабатывало и не могло сработать. Симметрично и тише: ON DELETE SET NULL у decisions.task_slug не удалял строку, а менял её, и файл решения продолжал называть удалённую задачу. Prevention: состав затронутых строк читается ИЗ СХЕМЫ через PRAGMA foreign_key_list по таблицам реестра ENTITY_DIRS и собирается транзитивно ДО удаления, поэтому проецируемый вид с каскадным внешним ключом покрывается той миграцией, которая его вводит, а не памятью автора. Обобщение вынесено в память #359: отношение, которым владеет движок, обязано читаться у движка. О предупреждении «COMPLEXITY UNDERSTATED: declared medium but touched 30 of 33»: ложное, четвёртый живой замер дефекта complexity-proxy-counts-state-projection. Фактическая работа — четыре файла: scripts/project_backend.py, tests/test_projection_shrinks_with_the_db.py (новый) и парные CHANGELOG. Остальные 29 — сгенерированная проекция БД.
