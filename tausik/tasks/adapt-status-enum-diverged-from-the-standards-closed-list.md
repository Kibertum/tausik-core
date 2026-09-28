---
slug: adapt-status-enum-diverged-from-the-standards-closed-list
title: "Закрытый перечень статусов ADAPT разошёлся со стандартом в обе стороны: лишний signed есть, обязательного approved нет"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: null
scope_exclude: "НЕ ТРОГАТЬ, ИСКЛЮЧЕНО ЗАМЕРОМ, А НЕ НАЗНАЧЕНИЕМ:\n(1) scripts/backend_migrations_v36.py — ИСТОРИЧЕСКИЙ снимок схемы на момент v36. По докстрингу v49 миграция не имеет права читать живую константу и не переписывается задним числом; правка сломала бы test_migration_v36_creates_tables_clean. Литерал из трёх значений там остаётся верным ДЛЯ СВОЕЙ ВЕРСИИ.\n(2) scripts/verify_receipt_emit.py — ЗАМЕРЕНО: STATUS_SIGNED там есть маркер исхода выпуска РАСПИСКИ verify (signed/no-key/error), проверено по строкам 60 и 128, к домену статусов ADAPT отношения не имеет. Не носитель.\n(3) scripts/project_cli_adapts.py:55 — res[signed] есть КЛЮЧ СЛОВАРЯ, возвращаемого adapt_verify, а не статус. Не носитель.\n(4) Точка контроля adapt-supersession и гейт check-adapt-supersession (§10.11.1) — ИСКЛЮЧЕНО ЗАМЕРОМ, НЕ УДОБСТВОМ: висячая ссылка, которую гейт обязан ловить, живёт в поле source.adapt на SPEC, а замер renar_clause_reactive_adapt.collect_state на живой БД даёт spec_provenance_columns=() — таких колонок НЕТ НИ ОДНОЙ. Гейт без субъекта есть вырожденный контроль по ADR-021, то есть ровно тот дефект, который эта задача чинит. Заводится отдельной задачей с зависимостью от появления провенанса SPEC."
relevant_files:
  - "scripts/backend_migrations_v50.py"
  - "scripts/backend_schema_adapts.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_crud_adapts.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_postseed.py"
  - "scripts/service_adapts.py"
  - "scripts/project_parser_adapts.py"
  - "scripts/project_cli_adapts.py"
  - "scripts/renar_drift.py"
  - "scripts/renar_conformance.py"
  - "scripts/renar_clause_reactive_adapt.py"
  - "harness/claude/mcp/project/tools_adapt.py"
  - "harness/claude/mcp/project/handlers_adapt.py"
  - "tests/test_migrations_v50_adapt_statuses.py"
  - "tests/test_adapts.py"
  - "tests/test_enum_single_source.py"
  - "tests/test_renar_drift.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_clause_reactive_adapt.py"
  - "tests/test_migrations_v49_spec_types.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - RENAR-CONFORMANCE.yaml
  - "n"
  - AGENTS.md
  - CLAUDE.md
  - "tausik/tasks/check-adapt-supersession-gate-has-no-subject-yet.md"
  - "tausik/memory/zakrytyy-perechen-imeet-chetyre-zerkala-i-ohrany-ne-bylo-u.md"
  - "tausik/memory/trebuemoe-standartom-sostoyanie-mozhet-byt-nedostizhimo-i.md"
  - "tausik/memory/mutatsiya-pokazavshaya-ekvivalentnost-eto-nahodka-o.md"
  - "tausik/memory/vetv-tselostnosti-srabatyvaet-tolko-na-slomannom-fiksturu.md"
scope_paths:
  - "scripts/"
  - "harness/"
  - "tests/"
  - "docs/"
  - CHANGELOG.md
scope_tools: []
depends_on:
  - our-conformance-claim-rests-on-a-mode-the-standard-removed
completed_at: "2026-09-04T14:56:37Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

НАЙДЕНО В #198 ПРИ ВЫНЕСЕНИИ ВЕРДИКТА ПО ADR-007. Единственное структурное несоответствие из шести: чинится не процессом, а миграцией схемы.

СТАНДАРТ, §7.8.1 стр.384 (цитата сверена машиной): «status: draft | review | asked | answered | approved | frozen | superseded» — семь значений, список закрытый.
МЫ, scripts/backend_schema_adapts.py:20: CHECK на ТРИ — «('draft', 'signed', 'superseded')».

ДВА СЛЕДСТВИЯ, ВТОРОЕ ТЯЖЕЛЕЕ.
(1) `signed` — значение, которого в закрытом перечне стандарта НЕТ. Мы завели собственный статус в списке, объявленном закрытым.
(2) `approved` — значение, которое §13.3.3 ТРЕБУЕТ для ветви findings-present («ADAPT обязателен в статусе `approved` с подписью Архитектора»), у нас ОТСУТСТВУЕТ. Наш ADAPT не может достичь требуемого статуса не по лени, а потому что CHECK-ограничение БД отклонит запись. Соответствие недостижимо без миграции.

СМЕЖНОЕ, ИЗ ТОГО ЖЕ ВЕРДИКТА, НЕ РАЗРЕЗАТЬ.
— `trigger-stage`, которым ADR-007 различает несколько ADAPT одного ТЗ, в схеме ОТСУТСТВУЕТ (негативная проверка прошла). Кардинальность 0..N мы формально не нарушаем при одном ADAPT, но выразить её не умеем.
— Дезавуирование наполовину есть и потому опаснее пустого места: статус `superseded` в enum ЕСТЬ, ребро `supersedes` в backend_schema.py:146 ЕСТЬ, а обязательного `supersession-rationale` (ADR-007 стр.108) НЕТ. Дезавуировать механически можно, сослаться на противоречащее требование — нельзя. Запись будет синтаксически валидной и содержательно пустой: вырожденный контроль по ADR-021, только в схеме данных.
— Точки контроля `adapt-supersession` (§10.11.1 стр.485) и обещанного самим ADR-007 гейта check-adapt-supersession у нас нет: висячая ссылка source.adapt на superseded ADAPT ничем не ловится.

ОГОВОРКА О ПОРЯДКЕ РАБОТ. Миграция enum осмысленна только вместе с решением по our-conformance-claim-rests-on-a-mode-the-standard-removed: если заявка о соответствии снимается, приводить схему к чужому закрытому списку — работа без адресата. Зависимость ставится в БД.

## Acceptance Criteria

AC-1: Закрытый перечень статусов ADAPT несёт ровно семь значений §7.8.1 (draft, review, asked, answered, approved, frozen, superseded); "signed" из перечня удалён. Проверяется на СВЕЖЕЙ схеме И на МИГРИРОВАННОЙ.
AC-2: Негативный сценарий — список остаётся ЗАКРЫТЫМ: INSERT со статусом вне семи отклоняется базой ошибкой sqlite3.IntegrityError, в том числе значением "signed" ПОСЛЕ миграции. Ошибка не проглатывается.
AC-3: Миграция v50 переносит строки status=signed в approved, идемпотентна (повторный вызов no-op) и пропускает себя на частичной фикстуре без таблицы adapts — иначе ошибка "no such table".
AC-4: CHECK базы ПРИШПИЛЕН к ADAPT_STATUSES тестом: расхождение субстрата и питоновского домена падает в CI. Сегодня эта дверь непокрыта.
AC-5: Все места, писавшие или читавшие "signed" как статус ADAPT, переведены на "approved" (service_adapts.sign, renar_drift, renar_conformance); ЧИСЛО мест закреплено тестом.
AC-6: adapts несёт trigger_stage и supersession_rationale (ADR-007 стр.108). Негативный сценарий: adapt_delta — ЕДИНСТВЕННЫЙ путь в superseded — без основания дезавуирования возвращает ошибку ServiceError, а не создаёт синтаксически валидную пустую запись.
AC-7: _check_adapt_approved сообщает недостижимость требуемого статуса НЕЗАВИСИМО от наличия ADAPT с backward-findings — вырожденная зелёная ветвь закрыта.
AC-8 (БЕЗОПАСНОСТЬ, ПРЕМИСА ПОПРАВЛЕНА ЗАМЕРОМ): расширение домена НЕ создаёт пути записи в approved в обход подписи Архитектора. Замер: adapt_set_status имеет РОВНО ДВА вызывающих места, оба внутренние (sign, adapt_delta); ни CLI, ни MCP статус не ПИШУТ — там он только ФИЛЬТР (project_parser_adapts.py:86, tools_adapt.py:110). Изначально я предполагал дыру и охрану против неё; замер премису опроверг, охрана без субъекта не строится. Вместо неё ЧИСЛО вызывающих мест закрепляется тестом, чтобы будущая команда set-status не сделала approved достижимым молча.
AC-9 (БЕЗОПАСНОСТЬ, целостность данных): перестройка идёт с PRAGMA foreign_keys=OFF, поэтому после неё PRAGMA foreign_key_check пуст, а число строк adapts и всех четырёх дочерних таблиц (interpretations, findings, signatures, links) до и после совпадает.

## Plan

## Rollback

git revert коммита + миграция односторонняя (как v49, по докстрингу run_migrations). Откат по данным безопасен ТОЛЬКО при отсутствии строк в статусах review/asked/answered/frozen/approved: при их наличии откат обязан быть решением о переносе, а не молчаливым сужением CHECK, который эти строки отвергнет. Схема возвращается на v49 правкой SCHEMA_VERSION и снятием ключа 50 из реестра.

## Journal

- 2026-09-04T12:27:24Z [implementation] — ИНВЕНТАРЬ ПО НИЖНЕМУ ПРИМИТИВУ (память #556), снят ДО оценки сложности. Примитив 1 — питоновский домен ADAPT_STATUSES (service_adapts.py:42). Потребители ПРИШПИЛЕНЫ tests/test_enum_single_source.py: project_parser_adapts.ADAPT_STATUS_CHOICES (выводится), tools_adapt._ADAPT_STATUSES (литерал, пришпилен), зеркало cursor (побайтовое сравнение). Прямые импортёры: renar_drift.py:41,131,137; service_adapts.py:85. Примитив 2 — CHECK базы, то есть то, что система РЕАЛЬНО примет: backend_schema_adapts.py:20 (свежий путь) и backend_migrations_v36.py:23 (исторический снимок). ЧЕТВЁРТАЯ ДВЕРЬ: CHECK НЕ пришпилен к ADAPT_STATUSES ничем. Сегодня они совпадают случайно, а не по контролю. Читатель домена в рантайме — renar_clause_reactive_adapt._status_domain, разбирающий DDL из sqlite_master. Примитив 3 — голый литерал signed мимо константы: service_adapts.py:183,204 (sign ставит статус); renar_conformance.py:150 (счёт adapts_signed) и он же кормит сигнал tz_immutable на :182; renar_drift.py:177 (полнота двойной подписи). Примитив 4 — доки со списком: docs/en/mcp.md:148, docs/ru/mcp.md:145. НЕ НОСИТЕЛИ, отсечены замером: verify_receipt_emit.STATUS_SIGNED (исход выпуска расписки verify, строки 60/128 — другой домен); project_cli_adapts.py:55 (ключ словаря res[signed], не статус). Тесты-носители: test_adapts.py:206,208,230; test_enum_single_source.py:65,79; test_renar_conformance.py:175,286; test_renar_drift.py:104,127; test_renar_clause_reactive_adapt.py:144. ИТОГО НЕСУЩИХ ФАЙЛОВ ~21 (11 production + 3 доки/CHANGELOG + 6 тестов + регенерируемый RENAR-CONFORMANCE.yaml). Сложность complex ПЕРЕОЦЕНЕНА ЗАНОВО по этому замеру, не унаследована. Бюджет вызовов переставлен вместе с ней: 120.
- 2026-09-04T12:28:47Z [implementation] — ПРЕМИСА AC-8 ОПРОВЕРГНУТА СОБСТВЕННЫМ ЗАМЕРОМ, ДО ПЕРВОЙ ПРАВКИ. Я объявил, что внесение approved в домен делает его установимым в обход подписи, и собирался строить охрану. Инвентарь по нижнему примитиву показал обратное: adapt_set_status (backend_crud_adapts.py:66) имеет РОВНО ДВА вызывающих места — service_adapts.py:204 (sign, при полной двойной подписи) и :255 (adapt_delta, в superseded). Пользовательского сеттера статуса НЕТ НИ В CLI, НИ В MCP: project_parser_adapts.py:86 объявляет --status только у list как ФИЛЬТР, tools_adapt.py:110 — тот же фильтр у tausik_adapt_list. Домен статусов участвует в записи только через эти два внутренних вызова. Строить охрану против несуществующего пути значило бы поставить контроль без субъекта — ровно вырожденный контроль по ADR-021, тот самый дефект, который эта задача чинит. Вместо охраны закрепляю ЧИСЛО вызывающих мест тестом (память #556): если появится команда set-status, тест покраснеет и заставит рассмотреть подпись. Это же правило применено к пункту 4 из смежных (гейт check-adapt-supersession): исключён замером spec_provenance_columns=() — колонки source.adapt, висячую ссылку в которой гейт обязан ловить, не существует.
- 2026-09-04T14:42:47Z [implementation] — МУТАЦИИ: ОБЪЯВЛЕНО 18, УБИТО 17, ЭКВИВАЛЕНТНЫХ 1, НЕВЫПОЛНЕННЫХ УБИЙСТВ 0. Базовый прогон rc=0. Знаменатель — число ОБЪЯВЛЕННЫХ (память #554); харнесс печатает несовпавшие якоря ОТДЕЛЬНОЙ категорией и НЕ считает их убийствами. ПЕРВЫЙ ПРОГОН ДАЛ 15/18, и все три отклонения оказались содержательными. (1) m13 — якорь встретился ДВАЖДЫ (except ValueError as e: есть и в adapt_create). Харнесс отказал вслух, а не заменил первое попадание. Переписан на многострочный уникальный якорь, мутант убит. (2) m04 — ЭКВИВАЛЕНТНЫЙ, и он вскрыл ЛОЖЬ В МОЁМ ЖЕ ДОКСТРИНГЕ. Я перенёс из v49 дословно утверждение «без снятия триггеров копирующий INSERT породил бы второй комплект записей в FTS». ЭТО НЕВЕРНО: копия идёт в НОВУЮ таблицу adapts_v50, а триггеры висят на adapts — на такой вставке они не срабатывают. Мутант, удаливший три DROP TRIGGER, выжил при ЗЕЛЁНОМ тесте на отсутствие дублей, то есть замер подтвердил эквивалентность. Докстринг и комментарий ИСПРАВЛЕНЫ: снятие остаётся ради явного порядка, но заявленной цены не имеет. Эквивалентность объявлена в харнессе ЗАРАНЕЕ, с причиной, а не подогнана после прогона. (3) m06 — выжил ЧЕСТНО: проверка PRAGMA foreign_key_check срабатывает только на СЛОМАННЫХ ссылках, а такой фикстуры не было ни одной. Непокрытая ветвь, а не слабое утверждение (память #552). Добавлены ДВА теста: висячая ссылка в adapt_findings -> RuntimeError, и ОТРИЦАНИЕ соседней корзины — та же фикстура без висячей строки миграцию не роняет (память #553). После этого m06 убит. ДОЛГ, НЕ В РАМКАХ ЭТОЙ ЗАДАЧИ: то же неверное утверждение про дублирование FTS стоит в scripts/backend_migrations_v49.py и, судя по формулировке, в v48/v24. Правка чужой исторической миграции — отдельное решение; предъявляю, не трогаю.
- 2026-09-04T14:52:52Z [implementation] — AC ЗАКРЫТЫ, КАЖДЫЙ ИМЕНОВАННЫМ ТЕСТОМ. AC-1: ✓ tests/test_migrations_v50_adapt_statuses.py::test_migrated_schema_carries_the_standard_list AC-2: ✓ tests/test_migrations_v50_adapt_statuses.py::test_our_old_signed_is_itself_rejected_after_migration AC-3: ✓ tests/test_migrations_v50_adapt_statuses.py::test_migration_is_idempotent AC-4: ✓ tests/test_enum_single_source.py::test_db_check_constraint_matches_adapt_statuses AC-5: ✓ tests/test_adapts.py::test_dual_signature_completes_and_verifies AC-6: ✓ tests/test_adapts.py::test_supersede_without_a_reason_is_refused AC-7: ✓ tests/test_renar_clause_reactive_adapt.py::test_unreachable_status_is_red_even_with_no_offending_rows AC-8: ✓ tests/test_adapts.py::test_status_write_sites_are_exactly_the_two_measured AC-9: ✓ tests/test_migrations_v50_adapt_statuses.py::test_rebuild_preserves_rows_children_and_integrity Negative: негативные сценарии проверены отдельными тестами, а не прицепом к положительным. Ошибка вне закрытого перечня — sqlite3.IntegrityError на СВЕЖЕЙ схеме (test_status_outside_the_list_is_rejected_on_fresh_schema) и на МИГРИРОВАННОЙ (test_status_outside_the_list_is_rejected_after_migration); отдельно проверено, что отвергается САМ наш прежний signed — иначе список был бы расширен, но не остался бы закрытым. Ошибка при дезавуировании без основания: ServiceError на сервисном слое и ValueError на НИЗШЕМ ПРИМИТИВЕ (test_the_rule_lives_at_the_lowest_primitive), плюс проверка, что пробелы не считаются основанием, плюс проверка, что родитель ОСТАЛСЯ ЖИВ после отказа. Ошибка при нарушенной целостности после перестройки — RuntimeError (test_broken_fk_integrity_stops_the_migration). Отсутствие таблицы на частичной фикстуре — ПРОПУСК, а не «no such table» (test_partial_fixture_without_adapts_is_skipped). ОТРИЦАНИЯ СОСЕДНИХ КОРЗИН добавлены там, где красное иначе было бы незаработанным (память #553): test_reachable_status_with_no_offending_rows_is_green, test_intact_fk_integrity_does_not_stop_the_migration, и в клаузульном тесте — утверждение, что фраза о недостижимости БОЛЬШЕ НЕ звучит, потому что субстрат теперь состояние держит. ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ СВЕРХ ОДНОГО НА AC: всего в новом файле 22, плюс 6 в test_adapts.py, плюс 2 в клаузульном, плюс 2 в test_enum_single_source.py.
- 2026-09-04T14:53:14Z [implementation] — ПОПРАВКА К ПРЕДЫДУЩЕЙ ЗАПИСИ: Я НАПИСАЛ 22, ФАКТ — 20. В новом файле tests/test_migrations_v50_adapt_statuses.py РОВНО 20 тестов, а не 22. Число я написал по памяти, не пересчитав командой, — ровно то завышение, против которого правило #558, и допустил я его в той же строке, где перечислял доказательства. СВЕРЕННЫЙ СЧЁТ НОВЫХ ТЕСТОВ (посчитан командой, не в уме): 20 в test_migrations_v50_adapt_statuses.py + 6 в test_adapts.py + 2 в test_renar_clause_reactive_adapt.py + 2 в test_enum_single_source.py = 30. НЕЗАВИСИМАЯ СВЕРКА СХОДИТСЯ: полная лента дала 8866 passed против 8836 на 96aa662, то есть ровно +30. Два независимых замера совпали, и это то, что делает число доказанным, а не заявленным.
- 2026-09-04T14:55:34Z [implementation] — ГЕЙТ FILESIZE ОТКЛОНИЛ ЗАКРЫТИЕ, И ОТКЛОНИЛ ПО ДЕЛУ. scripts/renar_conformance.py 504 при пределе 500. Передача смены предупреждала ИМЕННО про этот файл («ФАЙЛЫ У ПРЕДЕЛА 500: renar_conformance.py 499. Перед правкой у предела — выноси в модуль»), и я это предупреждение прочитал, но при правке не применил: заменяя одну строку запроса, я развернул её на шесть — трёхстрочный комментарий плюс вызов в четыре строки после форматтера. ПОЧИНКА: комментарий снят, вызов схлопнут в одну строку. Файл вернулся к ИСХОДНЫМ 499, а не к 500: сначала я сжал до 500 и увидел, что это ровно предел — то есть я оставил бы следующему правящему файл, который ломается от любой добавленной строки. Ухудшать запас на единицу и называть это «гейт пройден» — то же занижение, что и завышенный докстринг. ЗНАНИЕ НЕ ПОТЕРЯНО: почему принятая работа зовётся approved и куда делся signed — подробно в CHANGELOG (оба языка) и в докстринге scripts/backend_migrations_v50.py, то есть в местах, где у него есть место. ПРЕДЪЯВЛЯЮ ВЛАДЕЛЬЦУ: запас файла как был 1 строка, так и остался. Долг «renar_conformance.py у предела» из передачи #209 НЕ погашен и НЕ заведён; следующая правка этого файла обязана начинаться с выноса в модуль, иначе она упрётся в гейт так же, как упёрся я.
- 2026-09-04T14:57:06Z [done] — Domain: результат проверен ВНЕ тестов, на живом корпусе проекта, а не только на фикстурах. (1) Живая .tausik/tausik.db поднялась с версии 49 на 50 обычным вызовом doctor, без ручных шагов. Строка adapt-renar-adoption на месте, статус draft сохранён, обе новые колонки (trigger_stage, supersession_rationale) присутствуют в PRAGMA table_info, CHECK допускает approved. Ни одной строки не потеряно: adapts как был 1, так и остался 1. (2) СМЫСЛОВАЯ ПРОВЕРКА, а не только структурная: перегенерированный RENAR-CONFORMANCE.yaml (manifest-version 15) ИЗМЕНИЛ СВОЁ СВИДЕТЕЛЬСТВО по §13.3.3 ровно так, как обязан был. Было: «1 ADAPT carries backward findings but is not approved ... The substrate cannot even hold the required state: adapts.status admits [draft, signed, superseded], and approved is not among them». Стало: «1 ADAPT carries backward findings but is not approved (adapt-renar-adoption=draft)». То есть несоответствие из НЕДОСТИЖИМОГО стало ДОСТИЖИМЫМ к исправлению — это и есть предмет задачи, и он подтверждён артефактом, который считает сам себя, а не моим утверждением. (3) Ключ сырого счёта переименован согласованно: adapts_approved_count: 0 — ноль верен, потому что единственный ADAPT в статусе draft, подписей у него нет, и §13.3.3 по-прежнему обоснованно красная. Гейт не позеленел от переименования, и это правильный исход: если бы он позеленел, я бы чинил показания прибора вместо предмета. (4) Заявка уровня не затронута: level по-прежнему null, blocked-at scope-applicability (§1.5.4, решение #292). Расширение перечня статусов НЕ является путём назад к RENAR-N и таковым не стало.
- 2026-09-26T19:02:55Z [done] — EVIDENCE-MOVED: tests/test_adapts.py::test_dual_signature_completes_and_verifies => tests/test_adapts.py::test_the_architect_signature_alone_completes_and_verifies
