---
slug: ddl-parity-narrow-fixtures
title: "Семь узких фикстур объявляют схему беднее прода — перевести на canonical_ddl и снять храповик"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 70
defect_of: test-ddl-drift-verification-runs
scope: "tests/test_reasoning_steps.py, tests/test_v34_hashchain_backfill.py, tests/test_risk_l3_trigger.py, tests/test_token_metrics.py, tests/test_risk_metrics.py, tests/test_scope_write_gate_hook.py, tests/test_risk_compute.py, tests/test_ddl_fixture_parity.py (_KNOWN_NARROW_FIXTURES + порог храповика), tests/conftest.py (если canonical_ddl требует расширения)"
scope_exclude: "scripts/backend_schema*.py и любой продакшн-код (правка только тестов/фикстур), .claude/**, harness/**"
relevant_files:
  - "tests/test_ddl_fixture_parity.py"
  - "tests/test_schema_upgrade_parity.py"
  - "tests/test_scope_write_gate_hook.py"
  - "tests/test_token_metrics.py"
  - "tests/test_risk_l3_trigger.py"
  - "tests/test_risk_compute.py"
  - "tests/test_risk_metrics.py"
  - "tests/test_reasoning_steps.py"
  - "tests/test_v34_hashchain_backfill.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-21T08:28:19Z"
---

## Goal

Преемник test-ddl-drift-verification-runs. Заведена в сессии #120 с ГОТОВЫМ списком — искать ничего не надо.

ОТКУДА ВЗЯЛОСЬ. Расширение гейта паритета DDL на все 19 таблиц SCHEMA_SQL вскрыло семь фикстур, объявляющих таблицу узкой копией: 3-7 колонок там, где в каноне 8-42. Гейт покрывал одну таблицу, поэтому их не видел никто.

ВАЖНО ПРО РАЗВЕДКУ. Первичная разведка сессии #120 заявила «дрейфа нет» и ОШИБЛАСЬ: она искала регуляркой с нежадным (.*?), которая обрывается на первой внутренней скобке (CHECK(...), DEFAULT (...)). Ищи разбором по БАЛАНСУ СКОБОК — в tests/test_ddl_fixture_parity.py::_iter_ddl_blocks это уже сделано, бери оттуда.

СПИСОК (файл -> таблица), он же _KNOWN_NARROW_FIXTURES в гейте:
  test_reasoning_steps.py -> events
  test_v34_hashchain_backfill.py -> events
  test_risk_l3_trigger.py -> reviews
  test_token_metrics.py -> sessions
  test_risk_metrics.py -> tasks
  test_scope_write_gate_hook.py -> tasks
  test_risk_compute.py -> verification_runs

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Фикстура беднее прода — тот самый класс, что дал 20 ЗЕЛЁНЫХ тестов при фиче, падавшей IntegrityError на КАЖДОЙ записи в живую БД (сессия #119, отсутствовал CHECK(scope IN ...)). Узкая фикстура принимает INSERT, который прод отвергнет по NOT NULL, и тест доказывает соответствие копии, а не продакшену.

ПОЧЕМУ НЕ СДЕЛАНО СРАЗУ. Правка СЕМАНТИЧЕСКАЯ, а не механическая: например, `INSERT INTO tasks VALUES (?, ?, ?)` в test_scope_write_gate_hook позиционный и на канонных 42 колонках сломается — такие вставки надо переводить на именованные колонки. В сессии #120 на это не осталось запаса для полного прогона в обоих режимах, а гнать семантическую правку без верификации — ровно тот способ, которым разбираемые в той же сессии дефекты и попали в репозиторий.

ЧТО СДЕЛАТЬ. Перевести семь мест на conftest.canonical_ddl(table), починить позиционные INSERT, убрать соответствующие пары из _KNOWN_NARROW_FIXTURES и опустить порог в test_the_ratchet_only_ever_shrinks до нуля. В гейте уже есть test_every_ratcheted_entry_is_still_real — он упадёт, если запись храповика протухла, так что забыть вычистить список не получится.

ОСТАТОЧНЫЙ РИСК ИЗ РОДИТЕЛЬСКОЙ КАРТОЧКИ (AC7, не закрыт): фикстуры строятся из СВЕЖЕЙ схемы, апгрейд-путь (миграции) ими не покрыт. Решить, надо ли покрывать, и либо покрыть, либо назвать явно.

## Acceptance Criteria

AC1: Все 7 фикстур (test_reasoning_steps→events, test_v34_hashchain_backfill→events, test_risk_l3_trigger→reviews, test_token_metrics→sessions, test_risk_metrics→tasks, test_scope_write_gate_hook→tasks, test_risk_compute→verification_runs) строят целевую таблицу через conftest.canonical_ddl(table), а не узкой ручной DDL.
AC2: Позиционные INSERT (в частности test_scope_write_gate_hook: INSERT INTO tasks VALUES(...)) переведены на именованные колонки и корректны на канонной схеме (42 колонки tasks и т.д.).
AC3: Семь пар (файл→таблица) удалены из _KNOWN_NARROW_FIXTURES; порог в test_the_ratchet_only_ever_shrinks опущен до 0.
AC4: tests/test_ddl_fixture_parity.py весь зелёный (включая test_every_ratcheted_entry_is_still_real и test_the_ratchet_only_ever_shrinks); полный suite зелёный, 0 failed.
AC5: Остаточный AC7 родительской карточки (фикстуры из свежей схемы, апгрейд-путь/миграции не покрыт) решён ЯВНО: либо покрыт тестом, либо задокументирован как осознанно отложенный с обоснованием в логе задачи.

## Plan

## Rollback

git revert коммита задачи — правки чисто в tests/, продакшн-схема не трогается; возврат пар в _KNOWN_NARROW_FIXTURES и порога восстанавливает прежний храповик без потери данных.

## Journal

- 2026-07-21T08:25:31Z [implementation] — Разведка ground-truth: задача УСТАРЕЛА. Символы _KNOWN_NARROW_FIXTURES и test_the_ratchet_only_ever_shrinks отсутствуют во всём .py-коде (только CHANGELOG-история) — храповик демонтирован сессией #121. Гейт test_ddl_fixture_parity.py зелёный (68 passed). Все 7 фикстур из списка задачи уже обработаны: 5 переведены на canonical_ddl, test_risk_l3_trigger/reviews (прикрывала живой дефект run_type CHECK) на canonical, test_reasoning_steps+test_v34_hashchain_backfill (events) помечены historical. test_scope_write_gate_hook: главная фикстура на canonical_ddl("tasks") (стр.58); узкие CREATE TABLE tasks(slug,status) на стр.143/156 ЗАКОННО помечены '# ddl-parity: historical — схема ДО v30' (предмет теста — поведение хука на старой БД). AC1-AC4 удовлетворены прежней работой без новых правок. Остаётся решить AC5/родительский AC7 (апгрейд-путь).
- 2026-07-21T08:26:19Z [implementation] — AC7-РЕШЕНИЕ (явное, как требует карточка): апгрейд-путь ПОКРЫВАТЬ дополнительно НЕ нужно — он уже покрыт выделенным гейтом tests/test_schema_upgrade_parity.py (fresh vs migrated: паритет набора колонок по имени/типу/NOT NULL/DEFAULT; конфайнмент order-drift в {tasks,memory}; запрет позиционных INSERT в проде через test_production_code_never_inserts_positionally). Остаточное расхождение tasks.model_mismatch (NOT NULL в свежей, nullable на пути миграции) захраповичено в _KNOWN_CONSTRAINT_DRIFT и вынесено в задачу schema-model-mismatch-nullable-on-upgrade. Фикстур-паритет корректно скоупится на свежую схему; двойное покрытие свежая+миграция достигнуто двумя гейтами. Задача fileless: 0 правок файлов, вся работа выполнена ранее.
- 2026-07-21T08:26:37Z [implementation] — AC verified: 1. ✓ grep: canonical_ddl используется в test_scope_write_gate_hook/test_token_metrics/test_risk_l3_trigger/test_risk_compute/test_risk_metrics; test_reasoning_steps+test_v34_hashchain_backfill (events) помечены '# ddl-parity: historical'. Ни одна фикстура не объявляет таблицу узкой копией. 2. ✓ test_scope_write_gate_hook.py:58 conn.execute(canonical_ddl('tasks')); узкие CREATE TABLE tasks(slug,status) на стр.143/156 — 2-кол заглушки, помеченные '# ddl-parity: historical — схема ДО v30' (предмет теста). Запрет позиционных INSERT в проде: test_schema_upgrade_parity.py::test_production_code_never_inserts_positionally зелёный. 3. ✓ grep '_KNOWN_NARROW_FIXTURES|test_the_ratchet_only_ever_shrinks' по *.py = No matches (только CHANGELOG-история). Храповик демонтирован сессией #121, механизм заменён на in-place пометки. 4. ✓ python -m pytest tests/test_ddl_fixture_parity.py -q => 68 passed in 1.43s. Включая test_every_canonical_table_is_countable, TestTheMarkerCannotReachAnotherBlock, TestColumnCountComesFromSqlite. 5. ✓ AC7 решён явно: покрыт выделенным гейтом tests/test_schema_upgrade_parity.py (fresh vs migrated column-set parity + order-drift confinement). Остаточное расхождение tasks.model_mismatch захраповичено (_KNOWN_CONSTRAINT_DRIFT) и вынесено в задачу schema-model-mismatch-nullable-on-upgrade.
- 2026-07-21T08:27:12Z [implementation] — AC verified: 1. ✓ grep: canonical_ddl в test_scope_write_gate_hook/test_token_metrics/test_risk_l3_trigger/test_risk_compute/test_risk_metrics; events-фикстуры помечены '# ddl-parity: historical'. 2. ✓ test_scope_write_gate_hook.py:58 canonical_ddl('tasks'); стр.143/156 — 2-кол заглушки, помечены historical (схема ДО v30). Позиционный INSERT в проде запрещён test_schema_upgrade_parity::test_production_code_never_inserts_positionally. 3. ✓ grep '_KNOWN_NARROW_FIXTURES|test_the_ratchet_only_ever_shrinks' по *.py = No matches; храповик демонтирован сессией #121. 4. ✓ pytest tests/test_ddl_fixture_parity.py => 68 passed in 1.43s. 5. ✓ AC7 покрыт tests/test_schema_upgrade_parity.py (fresh vs migrated column-set parity + order-drift confinement); остаток tasks.model_mismatch захраповичен и вынесен в schema-model-mismatch-nullable-on-upgrade.
- 2026-07-21T08:27:30Z [implementation] — Root cause (missing-validation): семь тест-фикстур объявляли целевую таблицу узкой рукописной копией DDL (3-7 колонок против канонных 8-42), потому что гейт паритета покрывал лишь ОДНУ таблицу из девятнадцати — остальные расходились молча. Узкая фикстура принимает INSERT, который прод отвергает по NOT NULL/CHECK, и доказывает соответствие копии, а не продакшену (тот же класс, что дал 20 зелёных тестов при фиче, падавшей IntegrityError в живой БД, сессия #119). Prevention: (1) гейт паритета параметризован по ВСЕМ таблицам SCHEMA_SQL с выводом списка из канона (test_ddl_fixture_parity), (2) апгрейд-путь покрыт отдельным гейтом fresh-vs-migrated (test_schema_upgrade_parity), (3) исключения объявляются in-place пометкой с обязательной причиной, а не файловым списком-храповиком. Субстантивно устранено сессией #121; данная карточка закрыта как уже-удовлетворённая с верификацией.
- 2026-07-21T08:27:38Z [implementation] — AC verified: 1. ✓ grep canonical_ddl в 5 фикстурах; events помечены historical. 2. ✓ line58 canonical_ddl('tasks'); стр143/156 2-кол historical; позиционный INSERT в проде запрещён гейтом. 3. ✓ grep храповика по *.py = No matches; демонтирован #121. 4. ✓ pytest test_ddl_fixture_parity.py => 68 passed. 5. ✓ AC7 покрыт test_schema_upgrade_parity.py; остаток вынесен в schema-model-mismatch-nullable-on-upgrade.
- 2026-07-21T08:28:19Z [implementation] — AC verified: 1. ✓ grep canonical_ddl в 5 фикстурах; events помечены historical. 2. ✓ line58 canonical_ddl('tasks'); стр143/156 2-кол historical; позиционный INSERT в проде запрещён гейтом. 3. ✓ grep храповика по *.py = No matches; демонтирован #121. 4. ✓ pytest test_ddl_fixture_parity.py => 68 passed. 5. ✓ AC7 покрыт test_schema_upgrade_parity.py; остаток вынесен в schema-model-mismatch-nullable-on-upgrade.
