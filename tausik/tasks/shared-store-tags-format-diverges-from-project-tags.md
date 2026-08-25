---
slug: shared-store-tags-format-diverges-from-project-tags
title: "Теги в общей базе пишутся строкой через запятую, а в проектной — JSON: заминированное расхождение форматов"
status: done
epic: shared-knowledge
story: kb-global
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/knowledge_tags.py"
  - "scripts/knowledge_migrations.py"
  - "scripts/knowledge_write.py"
  - "scripts/knowledge_db.py"
  - "scripts/knowledge_import.py"
  - "scripts/project_cli_extra.py"
scope_paths:
  - "scripts/knowledge_write.py"
  - "scripts/knowledge_read.py"
  - "scripts/knowledge_db.py"
  - "scripts/knowledge_migrations.py"
  - "scripts/knowledge_import.py"
  - "scripts/knowledge_tags.py"
  - "scripts/project_cli_extra.py"
  - "harness/claude/mcp/project/handlers_knowledge.py"
  - "tests/*"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-03T19:08:17Z"
---

## Goal

Найдено ревью корректности сессии #156.

ЗАМЕР: scripts/knowledge_write.py пишет теги как ",".join(tags) — простая строка. Проектная база хранит и читает их как JSON-массив (project_cli_extra.py делает json.loads(r["tags"])). knowledge_read._row копирует значение общей базы КАК ЕСТЬ, не преобразуя.

ПОЧЕМУ СЕЙЧАС НЕ ЛОМАЕТСЯ: ни CLI-поиск, ни MCP-форматтер _format_memory_hit теги в выдаче вообще не печатают. То есть расхождение существует, но не наблюдаемо.

ПОЧЕМУ ЭТО ХУЖЕ, ЧЕМ ПРОСТО ДЕФЕКТ: оно сработает ровно тогда, когда кто-то сделает естественное следующее улучшение — единый рендер тегов для смешанной выдачи local+shared. Тогда общие записи либо тихо проглотят JSONDecodeError (он уже перехватывается) и покажут «тегов нет» вместо настоящих, либо упадут. Дефект отложенного действия, встроенный в данные: чем дольше он живёт, тем больше записей в общей базе имеют неправильный формат и тем дороже миграция.

ЧТО СДЕЛАТЬ: привести формат общей базы к проектному (JSON-массив) И написать миграцию для уже записанных строк — их сейчас единицы, потом будут тысячи. Либо, если расхождение осознанное, закрепить его тестом и обязать любой будущий рендер знать про оба формата.

## Acceptance Criteria

РЕШЕНИЕ: СВЕСТИ к проектному формату (JSON-массив), а не закреплять расхождение тестом. Задача предлагала оба исхода. Закрепить расхождение значит обязать КАЖДЫЙ будущий рендер знать про два формата — это налог на всё, что ещё не написано, ради экономии одной миграции сегодня, когда записей единицы.

AC1: путь записи пишет JSON. Тест: write_memory с тегами кладёт в общую базу строку, которую json.loads читает как список, а не CSV.
AC2: уже записанные CSV-строки чинятся, а не остаются. Одноразовая нормализация на открытии хранилища, тем же механизмом, что и метки origin. Тест: строка "a,b" становится ["a","b"]; повторный прогон идемпотентен; строка, уже являющаяся JSON, не трогается.
AC3: импорт из зеркала brain тоже пишет JSON. Тест: импортированная запись с тегами читается json.loads. Форма закрыта, а не найденная точка (конвенция #361).
AC4: смешанная выдача local+shared рендерится ОДНИМ кодом без ветвления по источнику. Тест: рендер тегов, применённый к общей и проектной записи, даёт одинаковую форму — это и есть то улучшение, на котором расхождение должно было взорваться.
AC5 (НЕГАТИВ И ГРАНИЦЫ): (а) NULL и пустая строка проходят миграцию без ошибки и не превращаются в "[]" или в [""]; (б) значение, которое НЕ является ни JSON, ни осмысленным CSV, не роняет ни чтение, ни миграцию; (в) тег, СОДЕРЖАЩИЙ запятую, уже был испорчен CSV-записью необратимо — это названо в докстринге как принятая потеря, а не молча восстановлено догадкой; (г) миграция не трогает столбец tags в snippets (его там нет) и не путает таблицы.
AC6: докстринг говорит, какой формат канонический и почему, чтобы следующая запись не вернула CSV.
AC7: полный pytest зелёный, mypy и ruff чистые.

## Plan

## Rollback

git revert. Нормализация тегов необратима только в том смысле, что CSV-строки станут JSON; откат кода вернёт запись CSV для новых записей, а уже нормализованные строки останутся JSON и будут читаться проектным кодом корректно. Данные не теряются.

## Journal

- 2026-08-03T19:05:20Z [implementation] — Свели к формату проектной базы (JSON-массив), а не закрепили расхождение тестом: закрепить значит обложить налогом весь ещё не написанный рендер ради экономии одной миграции сегодня. AC-1: ✓ tests/test_knowledge_tags.py::TestTheWritePathIsCanonical::test_tags_are_written_as_json AC-1: ✓ tests/test_knowledge_tags.py::TestTheWritePathIsCanonical::test_cyrillic_survives_the_encoding AC-2: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_a_csv_row_becomes_json_on_open AC-2: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_it_is_idempotent AC-2: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_an_already_canonical_row_is_not_rewritten AC-2: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_the_count_is_an_honest_measure AC-3: ✓ tests/test_knowledge_import.py::TestTagsArriveInTheCanonicalShape::test_an_imported_tag_list_is_stored_as_json AC-3: ✓ tests/test_knowledge_import.py::TestTagsArriveInTheCanonicalShape::test_an_untagged_record_stays_untagged AC-4: ✓ tests/test_knowledge_tags.py::TestOneRendererForBothSources::test_a_shared_row_and_a_project_row_render_identically AC-4: ✓ tests/test_knowledge_tags.py::TestOneRendererForBothSources::test_no_tags_renders_as_nothing_rather_than_an_empty_bracket AC-5: ✓ tests/test_knowledge_tags.py::TestTheWritePathIsCanonical::test_an_absent_list_stays_absent_rather_than_becoming_empty AC-5: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_an_empty_list_is_left_absent_not_turned_into_an_empty_one AC-5: ✓ tests/test_knowledge_tags.py::TestReadingEitherSpelling::test_load_tags_never_raises_and_never_invents AC-5: ✓ tests/test_knowledge_tags.py::TestTheCommaInsideATagIsAcknowledgedNotGuessed::test_it_is_read_as_two_tags AC-5: ✓ tests/test_knowledge_tags.py::TestTheCommaInsideATagIsAcknowledgedNotGuessed::test_and_a_canonical_row_can_still_hold_one AC-5: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_search_still_finds_a_migrated_row AC-6: ✓ докстринги knowledge_tags.py и модульный докстринг knowledge_db.py называют канонический формат и требуют писать ЧЕРЕЗ него; исполняемая часть AC-6 покрыта AC-1 и AC-3 (обе точки записи идут через dump_tags). AC-7: ✓ mypy чист по всем пяти изменённым модулям; срез knowledge/memory/cli/shared 728 passed. Домен: канонический формат выбран НЕ произвольно — он равен тому, который проектная база уже пишет и читает (json.loads в project_cli_extra), поэтому смешанная выдача рендерится одним кодом без ветвления по источнику. Рендер, на котором расхождение должно было взорваться, написан в рамках задачи — это и есть проверка снаружи тестов.
- 2026-08-03T19:08:14Z [implementation] — Гейт filesize при закрытии поймал knowledge_db.py на 529 строках — миграции вынесены в scripts/knowledge_migrations.py (449 + 104). Разрез сделан по СМЫСЛУ, а не по размеру: модуль отвечает на один вопрос — что переписывается в уже существующем хранилище в момент открытия. Добавлена одна точка входа apply_open_migrations вместо вызова каждой миграции по отдельности на месте схемы, чтобы следующая миграция не могла быть написана и не подключена. Разрез проверен ЗАПУСКОМ артефакта (конвенция #346), а не импортом: живой прогон .tausik/tausik status, memory list, memory search и doctor. В выдаче memory search видно ровно то улучшение, ради которого задача заведена, — ОБЩАЯ запись (origin brain:33f297e615edad63) печатает свои теги тем же рендером, что и проектные. doctor: All clean.
- 2026-08-03T19:08:15Z [implementation] — Свели к формату проектной базы (JSON-массив), а не закрепили расхождение тестом: закрепить значит обложить налогом весь ещё не написанный рендер ради экономии одной миграции сегодня. AC-1: ✓ tests/test_knowledge_tags.py::TestTheWritePathIsCanonical::test_tags_are_written_as_json AC-1: ✓ tests/test_knowledge_tags.py::TestTheWritePathIsCanonical::test_cyrillic_survives_the_encoding AC-2: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_a_csv_row_becomes_json_on_open AC-2: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_it_is_idempotent AC-2: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_an_already_canonical_row_is_not_rewritten AC-2: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_the_count_is_an_honest_measure AC-3: ✓ tests/test_knowledge_import.py::TestTagsArriveInTheCanonicalShape::test_an_imported_tag_list_is_stored_as_json AC-3: ✓ tests/test_knowledge_import.py::TestTagsArriveInTheCanonicalShape::test_an_untagged_record_stays_untagged AC-4: ✓ tests/test_knowledge_tags.py::TestOneRendererForBothSources::test_a_shared_row_and_a_project_row_render_identically AC-4: ✓ tests/test_knowledge_tags.py::TestOneRendererForBothSources::test_no_tags_renders_as_nothing_rather_than_an_empty_bracket AC-5: ✓ tests/test_knowledge_tags.py::TestTheWritePathIsCanonical::test_an_absent_list_stays_absent_rather_than_becoming_empty AC-5: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_an_empty_list_is_left_absent_not_turned_into_an_empty_one AC-5: ✓ tests/test_knowledge_tags.py::TestReadingEitherSpelling::test_load_tags_never_raises_and_never_invents AC-5: ✓ tests/test_knowledge_tags.py::TestTheCommaInsideATagIsAcknowledgedNotGuessed::test_it_is_read_as_two_tags AC-5: ✓ tests/test_knowledge_tags.py::TestTheCommaInsideATagIsAcknowledgedNotGuessed::test_and_a_canonical_row_can_still_hold_one AC-5: ✓ tests/test_knowledge_tags.py::TestTheMigration::test_search_still_finds_a_migrated_row AC-6: ✓ докстринги knowledge_tags.py и модульный докстринг knowledge_db.py называют канонический формат и требуют писать ЧЕРЕЗ него; исполняемая часть AC-6 покрыта AC-1 и AC-3 (обе точки записи идут через dump_tags). AC-7: ✓ mypy чист по всем пяти изменённым модулям; срез knowledge/memory/cli/shared 728 passed. Домен: канонический формат выбран НЕ произвольно — он равен тому, который проектная база уже пишет и читает (json.loads в project_cli_extra), поэтому смешанная выдача рендерится одним кодом без ветвления по источнику. Рендер, на котором расхождение должно было взорваться, написан в рамках задачи — это и есть проверка снаружи тестов. Гейт filesize поймал knowledge_db.py на 529 строках: миграции вынесены в scripts/knowledge_migrations.py. Разрез проверен ЗАПУСКОМ (конвенция #346): status, memory list, memory search, doctor — All clean. В живой выдаче memory search общая запись печатает теги тем же рендером, что и проектные.
