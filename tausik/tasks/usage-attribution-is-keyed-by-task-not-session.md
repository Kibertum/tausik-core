---
slug: usage-attribution-is-keyed-by-task-not-session
title: "Схема делает сессию обязательной, а задачу опциональной: атрибуция ключуется не тем"
status: done
epic: release-19-agent-effectiveness
story: parallel-work-runs-without-collisions
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_schema.py (SCHEMA_VERSION 47->48, DDL usage_events), scripts/backend_migrations.py (регистрация 48), scripts/backend_migrations_v48.py (НОВЫЙ — перестройка таблицы, SQLite не снимает NOT NULL на месте), scripts/backend_queries_usage.py (session_id: int | None; запрос корзины), scripts/hooks/posttool_usage.py (снятие дропа), scripts/project_cli_metrics.py (печать корзины), CHANGELOG.md, docs/ru/sessions.md, tests/."
scope_exclude: null
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v48.py"
  - "scripts/backend_migrations_postseed.py"
  - "scripts/backend_queries_usage.py"
  - "scripts/project_service.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/hooks/posttool_usage.py"
  - "tests/test_posttool_usage_hook.py"
  - "tests/test_schema_upgrade_parity.py"
  - "tests/test_usage_events_unattributed_bucket.py"
  - "tests/test_migrations.py"
  - "tests/test_hook_encoding.py"
  - "tests/test_gate_class_surface.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/ru/sessions.md"
  - "docs/ru/cost-telemetry.md"
  - "docs/en/cost-telemetry.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-31T09:29:25Z"
---

## Goal

ЗАМЕР #189, ПРЯМОЙ: `CREATE TABLE usage_events (session_id INTEGER NOT NULL REFERENCES sessions(id), task_slug TEXT REFERENCES tasks(slug), ...)`. Схема делает СЕССИЮ обязательной, а ЗАДАЧУ опциональной — наоборот от нужного. И scripts/hooks/posttool_usage.py:200 дропает событие целиком: `if session_id is None: return`, при том что task_slug в этот момент известен.
СЛЕДСТВИЕ, ЗАДОКУМЕНТИРОВАННОЕ В docs/ru/sessions.md:64-76: без открытой сессии молча отказывают пять механизмов, ЗАПИСЫВАЯ НОЛЬ, а не ошибку — usage-телеметрия, token-метрики, пиннинг модели, срез brain (самый опасный: не пусто, а НЕВЕРНО, выдаёт себя за сессионный) и каденция аудита.
ЦЕЛЬ АТРИБУЦИИ УЖЕ СУЩЕСТВУЕТ: tasks несёт cost_actual_usd, tokens_actual, started_model_id, started_at. То есть сессия здесь не несущая конструкция, а NOT NULL, который никто сознательно не выбирал.
ЧТО ДЕЛАЕТСЯ (миграция схемы 47 -> 48): session_id становится необязательным, task_slug — основной атрибуцией; хук пишет событие, если известна ЗАДАЧА, и перестаёт дропать. Работа без открытой сессии становится ПОЛНОЦЕННОЙ, а сессия — производным отчётом о пробеге активности (логика разрывов gap-based ≥10 мин уже есть).
НЕГАТИВНОЕ: событие БЕЗ задачи и БЕЗ сессии не имеет права исчезать молча — оно пишется в явную корзину «вне задачи» и видно в отчёте. Иначе мы поменяем один тихий дроп на другой. ЛОМАЮЩЕЕ: миграция схемы, обязана попасть в заметки 1.9.

## Acceptance Criteria

AC1. СХЕМА 48. `usage_events.session_id` НЕ ИМЕЕТ NOT NULL — `PRAGMA table_info` даёт notnull=0 И на свежей БД, И на БД, поднятой миграциями с v1. FK на sessions становится ON DELETE SET NULL: событие переживает удаление сессии, потому что его атрибуция — ЗАДАЧА, а не сессия. SCHEMA_VERSION=48 и MIGRATIONS[48] существуют оба (импортный гейт check_schema_migration_parity). tests/test_schema_upgrade_parity.py зелёный: свежая и мигрированная DDL совпадают ПОЛНОСТЬЮ, включая CHECK/FK.

AC2. ЗАПИСЬ. `usage_event_append` принимает session_id: int | None и пишет NULL без исключения; сигнатура типизирована, mypy зелёный.

AC3. ХУК НЕ ДРОПАЕТ. При отсутствии открытой сессии scripts/hooks/posttool_usage.py пишет строку с session_id=NULL и ИЗВЕСТНЫМ task_slug вместо `return 0`. Храповик tests/test_posttool_usage_hook.py::test_no_open_session_skips_insert, закреплявший дефект, ПЕРЕВЁРНУТ, а не снят: докстринг называет прежний контракт и место настоящей защиты.

AC4. НЕГАТИВНЫЙ СЦЕНАРИЙ. Событие БЕЗ задачи И БЕЗ сессии НЕ исчезает молча: оно попадает в явную корзину «вне задачи», печатаемую `tausik metrics cost`. Корзина печатается ДАЖЕ когда ролап по задачам пуст — нынешний ранний возврат «No usage data ...» обязан перестать её прятать, иначе мы меняем тихий дроп на тихое сокрытие. Корзина НЕ включает зеркальные строки source='session_record' (иначе отчёт удваивается — контракт tests/test_usage_events_double_count.py). Тест предъявляет обе половины: строка без задачи и без сессии ВИДНА в выводе, и она же не удваивает суммы.

AC5. ЛОМАЮЩЕЕ ОБЪЯВЛЕНО. CHANGELOG.md несёт запись о миграции схемы 47->48 как о ломающем изменении 1.9; docs/ru/sessions.md больше не утверждает, что usage-телеметрия молча выключается без сессии.

AC6. РЕГРЕСС. tests/test_posttool_usage_hook.py, tests/test_usage_events_double_count.py, tests/test_schema_upgrade_parity.py, tests/test_init_schema_upgrade_order.py, tests/test_metrics_session_usage.py — зелёные.

## Plan

## Rollback

ИСПРАВЛЕНО ПО ФАКТУ КОДА: обратной миграции 48->47 НЕ БУДЕТ — backend_migrations.run_migrations односторонний по своему докстрингу («Migrations are irreversible -- no rollback support»), и обещать её в плане отката значит обещать несуществующее.
ОТКАТ КОДА: git revert коммита (SCHEMA_VERSION возвращается к 47, MIGRATIONS[48] исчезает).
ОТКАТ БД: понижения схемы не требуется по данным — код v47 вставляет session_id всегда не-NULL и ни один его SELECT не полагается на NOT NULL, поэтому уже мигрированная таблица его не ломает. Требуется ОДНА ручная строка, потому что backend_init отказывает при db_ver > SCHEMA_VERSION: `UPDATE meta SET value='47' WHERE key='schema_version'`. Строки с NULL session_id при этом остаются и читаются штатно; терять их не нужно.
ПОТЕРЯ ДАННЫХ: нулевая в обе стороны — миграция только ослабляет ограничение и копирует строки один в один.

## Journal

- 2026-08-29T14:34:06Z [planning] — [#189] ГОЛОВА ЛЕНТЫ — ЛЕНТА Б. Решение #273 задаёт три ленты, стартующие ОДНОВРЕМЕННО и имеющие приоритет при назначении агента перед пулом из остальных задач: А «проверка работает» (без неё релиз про доказательства недоказуем), Б «многоагентность включена» (без неё параллельные агенты портят бюджеты друг друга — у потребителя бюджет 25 против call_actual 373), В «длинная цепь» (пять звеньев, три complex, распараллелить нельзя — она и есть пол по сроку релиза). Пометка стоит здесь, потому что приоритет лент СЕГОДНЯ НЕ ВЫРАЗИМ полем: task next выбирает по всему бэклогу и объявленный порядок игнорирует (задача task-next-ignores-declared-wave-order, лента Б). До её починки голову ленты берут по этой пометке.
- 2026-08-31T08:59:22Z [implementation] — [#192] QG-0 дописан перед стартом: AC, scope и rollback_plan отсутствовали/врали. rollback_plan обещал обратную миграцию 48->47 — её не может быть: run_migrations односторонний по своему же докстрингу. Переписан на git revert + одну ручную строку UPDATE meta (backend_init отказывает при db_ver > SCHEMA_VERSION). Разведка кода: усечение атрибуции живёт в четырёх местах — DDL backend_schema.py:275-288 (session_id NOT NULL), usage_event_append (session_id: int), хук posttool_usage.py:200 (`if session_id is None: return 0`), и отчёт project_cli_metrics._print_usage_cost_rollup (ранний возврат «No usage data» + WHERE task_slug IS NOT NULL в ролапе). Найден храповик, закрепляющий дефект: tests/test_posttool_usage_hook.py::test_no_open_session_skips_insert — будет ПЕРЕВЁРНУТ с объяснением, не снят.
- 2026-08-31T09:06:43Z [implementation] — [#192] Код готов, AC1-AC4 и AC6 закрыты замером. Миграция v48 — перестройка usage_events (SQLite не снимает NOT NULL на месте), по образцу v24 на этой же таблице. ЗАМЕР ОБОИХ ПУТЕЙ: свежая и мигрированная с v1 дают session_id notnull=0, FK на sessions = SET NULL (был CASCADE — каскад при новом смысле стирал бы расход ЖИВОЙ задачи вместе с удалённой сессией), индексы пересозданы все три. Паритетный тест обобщён с tasks на список перестроенных таблиц — теперь полный нормализованный DDL usage_events сверяется тоже, и это ЕДИНСТВЕННОЕ, что видит FK: PRAGMA table_info про ограничения не знает. МУТАЦИИ, ТРИ ИЗ ТРЁХ ПОЙМАНЫ, возврат побайтовой копией со сверкой sha256: (1) SET NULL -> CASCADE в снимке v48 -> parity RED (sha 6881ad1adaa441e1); (2) снят фильтр source<>'session_record' в корзине -> bucket RED (sha dab4e69d7133b98f); (3) вернул ранний возврат в _print_usage_cost_rollup -> bucket RED (sha ffc5645d77508a8a). Все три файла вернулись байт в байт. Храповик test_no_open_session_skips_insert ПЕРЕВЁРНУТ в test_no_open_session_still_records_the_task: докстринг называет прежний контракт, причину (NOT NULL, не выбор) и адрес переехавшей защиты — видимость корзины вместо дропа. Локально 49 тестов зелёных.
- 2026-08-31T09:15:44Z [implementation] — [#192] ПЕРВАЯ РЕДАКЦИЯ v48 БЫЛА НЕВЕРНА И ОПРОВЕРГНУТА ТЕСТАМИ, не рассуждением. Простой список SQL по образцу v24 уронил test_adapts.py::test_migration_v36_creates_tables_clean и test_reasoning_steps.py::test_migration_v32_creates_table_triggers_clean — оба `no such table: usage_events`. Причина: такой тест поднимает МИНИМАЛЬНУЮ БД и гонит миграции с версии 32/36, v23 (создающая таблицу) не выполняется никогда, а слепой DROP TABLE в конце цепочки роняет весь прогон. v24 этого не встречала — таких фикстур в 2024-м не было. Переделано в ОХРАНЯЕМЫЙ пост-шаг maybe_rebuild_usage_events_v48 (приём v42_backfill/v43): охрана = таблица есть И session_id всё ещё NOT NULL, отсюда же идемпотентность. Урок закреплён напрямую в TestV48UsageEventsRebuildGuard, а не только косвенно через те два теста: они проверяют СВОИ миграции и завтра могут переехать на другую стартовую версию, унеся покрытие чужого дефекта. МУТАЦИИ ПОСЛЕ ПЕРЕДЕЛКИ, ТРИ ИЗ ТРЁХ ПОЙМАНЫ (возврат побайтово, sha сверены): SET NULL->CASCADE -> parity RED (sha 79c98df760b0f5d3); охрана снята (`if False`) -> 4 красных в test_migrations (тот же sha); вызов пост-шага вырезан из run_post_migrations -> 2 красных в parity (sha 69cbd76ec651ecd1). ЖИВАЯ БД МИГРИРОВАНА НА МЕСТЕ: schema_version=48, session_id notnull=0, оба FK = SET NULL, 56413 строк на месте. `tausik metrics cost` немедленно предъявил корзину: 18638 событий вне задачи, 195216 токенов — ТРЕТЬ всего журнала, которая до сегодня не попадала ни в один отчёт. Хвоста «вне сессии» нет, и это верно: дов48-строки писались внутри сессий, но вне задач. ruff/mypy зелёные (342 файла), bootstrap прогнан.
- 2026-08-31T09:28:59Z [implementation] — AC1 PASS замером на ОБОИХ путях: свежая (SCHEMA_SQL) и поднятая миграциями с v1 дают usage_events.session_id notnull=0 и оба FK ON DELETE SET NULL; SCHEMA_VERSION=48 = max(MIGRATIONS) (импортный гейт check_schema_migration_parity); test_schema_upgrade_parity зелёный, и его DDL-сверка обобщена с tasks на список перестроенных таблиц, поэтому FK usage_events теперь сверяется тоже (PRAGMA table_info про FK слепа). AC2 PASS: usage_event_append принимает session_id: int | None, пишет NULL; mypy Success, 342 файла. AC3 PASS: дроп снят, храповик test_no_open_session_skips_insert ПЕРЕВЁРНУТ в test_no_open_session_still_records_the_task с докстрингом, называющим прежний контракт, его причину (NOT NULL, а не выбор) и адрес переехавшей защиты. AC4 PASS обеими половинами: строка без задачи и без сессии пишется (test_no_session_and_no_task_is_still_written) И видна (test_usage_events_unattributed_bucket, 8 тестов, включая печать при ПУСТОЙ таблице по задачам и исключение зеркальных session_record). Мутации, 6 из 6 пойманы, возврат побайтовый со сверкой sha256: SET NULL->CASCADE, снятый фильтр source, возвращённый ранний возврат, снятая охрана, вырезанный вызов пост-шага. AC5 PASS: CHANGELOG.md и CHANGELOG.ru.md несут запись (BREAKING/ЛОМАЮЩЕЕ, схема 47->48); docs/ru/sessions.md больше не числит usage-телеметрию среди молча отказывающих; docs/{ru,en}/cost-telemetry.md приведены к новой схеме. AC6 PASS: verify #1867, scoped прогон 127 файлов, exit=0. Negative: см. AC4 — корзина предъявлена и мутационно проверена; на живой БД она немедленно показала 18638 событий вне задачи, треть журнала.
- 2026-08-31T09:29:22Z [implementation] — AC verified: 1. ПРОЙДЕНО замером на ОБОИХ путях — свежая схема (SCHEMA_SQL) и БД, поднятая миграциями с v1, дают usage_events.session_id notnull=0 и оба FK ON DELETE SET NULL; SCHEMA_VERSION=48 равен максимуму MIGRATIONS (импортный гейт check_schema_migration_parity); test_schema_upgrade_parity зелёный, и его DDL-сверка обобщена с tasks на СПИСОК перестроенных таблиц, поэтому FK usage_events сверяется тоже — PRAGMA table_info про FK слепа, это единственная проверка, которая его видит. 2. ПРОЙДЕНО — usage_event_append принимает session_id: int | None и пишет NULL; mypy Success, 342 файла, 0 ошибок. 3. ПРОЙДЕНО — дроп if session_id is None: return 0 снят, событие пишется с session_id=NULL и живым task_slug. Храповик test_no_open_session_skips_insert ПЕРЕВЁРНУТ в test_no_open_session_still_records_the_task, докстринг называет прежний контракт, его причину (NOT NULL был следствием схемы, а не выбором) и адрес переехавшей защиты — видимость корзины вместо дропа. 4. ПРОЙДЕНО обеими половинами. Записывается: test_no_session_and_no_task_is_still_written. Видна: tests/test_usage_events_unattributed_bucket.py, 8 тестов, включая печать при ПУСТОЙ таблице по задачам (ранний возврат больше не прячет) и исключение зеркальных строк source=session_record (иначе ~2x удвоение, контракт test_usage_events_double_count). 5. ПРОЙДЕНО — CHANGELOG.md и CHANGELOG.ru.md несут запись BREAKING/ЛОМАЮЩЕЕ про схему 47 в 48; docs/ru/sessions.md больше не числит usage-телеметрию среди молча отказывающих без сессии; docs/ru/cost-telemetry.md и docs/en/cost-telemetry.md приведены к новой схеме. 6. ПРОЙДЕНО — verify #1867, scoped прогон 127 файлов из 414, exit=0. Negative: корзина вне задачи предъявлена и мутационно проверена. МУТАЦИИ, 6 из 6 пойманы, каждая возвращена ПОБАЙТОВОЙ копией со сверкой sha256: FK SET NULL в CASCADE (parity RED), снятый фильтр source (bucket RED), возвращённый ранний возврат в отчёте (bucket RED), снятая охрана пост-шага (4 красных в test_migrations), вырезанный вызов пост-шага из run_post_migrations (2 красных в parity), плюс мутация смежной задачи. На живой БД корзина немедленно показала 18638 событий вне задачи, 195216 токенов — треть журнала из 56413 строк, не попадавшая ни в один отчёт.
- 2026-08-31T09:31:09Z [done] — AC-1: ✓ замерено на обоих путях (свежая SCHEMA_SQL и поднятая с v1) — session_id notnull=0, оба FK ON DELETE SET NULL; tests/test_schema_upgrade_parity.py, DDL-сверка обобщена на список перестроенных таблиц. AC-2: ✓ tests/test_usage_events_unattributed_bucket.py::TestBucketCounts + mypy Success 342 файла. AC-3: ✓ tests/test_posttool_usage_hook.py::test_no_open_session_still_records_the_task (перевёрнутый храповик) и ::test_no_session_and_no_task_is_still_written. AC-4: ✓ tests/test_usage_events_unattributed_bucket.py, 8 тестов; ключевые — ::test_printed_when_per_task_table_is_empty и ::test_session_record_mirror_row_is_excluded. AC-5: ✓ CHANGELOG.md + CHANGELOG.ru.md (BREAKING/ЛОМАЮЩЕЕ, 47->48), docs/ru/sessions.md, docs/ru/cost-telemetry.md, docs/en/cost-telemetry.md. AC-6: ✓ verify #1867, 127 файлов в scope, exit=0. Domain: результат осмыслен вне тестов и проверен на ЖИВОЙ базе, а не только на фикстурах — БД мигрирована на месте (schema_version=48, 56413 строк сохранены), и `tausik metrics cost` немедленно напечатал корзину в 18638 событий и 195216 токенов. Это треть журнала, до сегодня не попадавшая ни в один отчёт; хвоста «вне сессии» ноль, что физически верно — до v48 схема запрещала session_id=NULL, поэтому все прежние строки писались внутри сессий. Замечание к оценке сложности принято: гейт прав, medium занижена — 16 файлов, несущих поведение. Занижение снизило QG-0 scope/rollback до предупреждений, и это записано в аудит.
