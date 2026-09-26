---
slug: ar-existence-is-probed-by-three-guessed-table-names
title: "Существование AR как класса артефактов проверяется угаданным перечнем трёх имён, и манифест эти имена публикует"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "Схема БД не меняется (миграций нет); TC-предпосылка renar_tc_premise не переписывается — переиспользуется artifact_classes; клауза §13.3.3 и её остальные под-проверки не трогаются; таблица reviews не объявляется AR"
relevant_files:
  - "scripts/renar_clause_reactive_adapt.py"
  - "tests/test_renar_clause_reactive_adapt.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_export.py"
  - RENAR-CONFORMANCE.yaml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/renar_clause_reactive_adapt.py"
  - "scripts/renar_tc_premise.py"
  - "tests/test_renar_clause_reactive_adapt.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_export.py"
  - "tests/test_renar_tc_premise.py"
  - RENAR-CONFORMANCE.yaml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T20:18:11Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАВЕДЕНА ПО ЖИВОМУ ЗАМЕРУ В #202 ПРИ ЗАКРЫТИИ adr-013-conditional-obligations-expire-when-subject-appears. ИНВЕНТАРЬ СДЕЛАН ДО ОЦЕНКИ.

ЧТО ИЗМЕРЕНО. В scripts/renar_clause_reactive_adapt.py:60 стоит AR_TABLE_CANDIDATES равное трём именам: adversarial_reviews, ar_records, renar_ar. Существование AR как КЛАССА артефактов решается принадлежностью к этому перечню. Это ровно тот дефект, который в #202 был найден мутацией для TC и там починен: разрез назван угаданными именами, а обещание сделано про предмет. Мутация, закрывшая ту задачу, была таблицей spec_tests — имя, которого в перечне не было.

ОТЯГЧАЮЩЕЕ: ИМЕНА ПУБЛИКУЮТСЯ. RENAR-CONFORMANCE.yaml печатает в evidence строку probed со всеми тремя именами, то есть манифест предъявляет ВНЕШНЕМУ ЧИТАТЕЛЮ перечень имён как доказательство отсутствия класса. Вес поля повышен публикацией (память #483).

НАПРАВЛЕНИЕ РИСКА ЗДЕСЬ ОБРАТНОЕ ЗАДАЧЕ ПРО TC, И ЭТО ВАЖНО ДЛЯ ОЦЕНКИ СРОЧНОСТИ. Там публиковалось true, которое могло стать ложным. Здесь ok равно false: если AR появится под неугаданным именем, мы продолжим публиковать «AR не существует» и тем самым ЗАНИЗИМ собственную заявку. По решению #295 усиливающая поправка сообщается наружу ВСЕГДА, значит пропуск здесь есть невыполненная обязанность сообщить, а не просто неточность.

ПРИЁМ ГОТОВ И КОПИРОВАТЬ ЕГО НЕЛЬЗЯ. В #202 заведён scripts/renar_tc_premise.py с функцией artifact_classes, которая перечисляет классы артефактов, выводя теневые таблицы FTS из владеющей виртуальной таблицы, а не по префиксу. Предмет здесь ДРУГОЙ (AR, не TC) и клауза другая (§13.3.3 p.73 против §13.3.5), поэтому по решению #296 это отдельная задача — но общий класс дефекта есть основание ПЕРЕИСПОЛЬЗОВАТЬ artifact_classes, а не писать четвёртый перечень имён.

ОТКРЫТЫЙ ВОПРОС, КОТОРЫЙ ПРИДЁТСЯ РЕШИТЬ ВНУТРИ ЗАДАЧИ. Комментарий на строке 57 честно говорит, что таблица reviews НЕ засчитывается: она пишет ревью закрытия задачи и её кода, а AR есть вердикт ревью ТЗ. Значит одного перечисления классов недостаточно: нужен признак, отличающий AR от обычного ревью, и он не должен быть новым угаданным именем. Ответ ищи замером, а не рассуждением.

## Acceptance Criteria

AC1 СУЩЕСТВОВАНИЕ КЛАССА AR ОПРЕДЕЛЯЕТСЯ ФОРМОЙ ПО §7.4.6, НЕ ИМЕНЕМ: среди artifact_classes(conn) из renar_tc_premise (теневые FTS исключены выводом, не префиксом) AR-классом считается таблица, чьи колонки несут ссылку на ТЗ (tz_ref), verdict и status; AR_TABLE_CANDIDATES удалён из кода; evidence под-проверки adversarial-review-issued называет ПРИЗНАК (обязательные поля §7.4.6) и то, почему reviews не подходит (task_slug/run_type — не tz_ref/verdict), а не перечень угаданных имён; RENAR-CONFORMANCE.yaml перегенерирован командой и строки probed [...] в нём нет.
AC2 НЕГАТИВНЫЙ СЦЕНАРИЙ (мутации, каждая убита названным тестом): AR-таблица под неугаданным именем (tz_review_verdicts) с tz_ref/verdict/status и строкой issued — collect_state находит её и под-проверка зелёная (на HEAD — красная «AR does not exist»); таблица reviews живой схемы не засчитывается; таблица с tz_ref и status, но без verdict — не засчитывается, evidence называет недостающее поле; таблица по форме, но без строки issued — красный «zero AR in status issued»; ошибка перечня: две таблицы по форме — evidence называет обе, issued суммируется.
AC3 ПОТРЕБИТЕЛИ В tests/ ПЕРЕВЕДЕНЫ НА ФОРМУ: фикстуры test_renar_clause_reactive_adapt, test_renar_conformance, test_renar_export создают AR со всеми тремя полями (tz_ref, verdict, status), а не с именем из перечня; scoped зелёный; ruff/mypy чисто; renar_clause_reactive_adapt.py <= 500 строк (при выносе — отдельный модуль).
AC4 CHANGELOG.md и CHANGELOG.ru.md синхронно; bootstrap --ide all перед done (правится scripts/), verify после него перезапущен; память ДО done.

## Plan

## Rollback

git revert коммита задачи. Миграций не требуется: проверка только ЧИТАЕТ sqlite_master. RENAR-CONFORMANCE.yaml откатывается тем же revert и перегенерируется командой tausik renar conformance.

## Journal

- 2026-09-03T20:08:01Z [implementation] — СТАРТ. Инвентарь до оценки, по вызову и по классу: AR_TABLE_CANDIDATES — одно несущее место (renar_clause_reactive_adapt.py:60,136,198: перечень, выбор в collect_state, строка evidence); потребители в tests/: фикстуры adversarial_reviews в test_renar_clause_reactive_adapt (2, без verdict), test_renar_conformance (1, без verdict), test_renar_export (1, с verdict); публикация — RENAR-CONFORMANCE.yaml:124 probed [...]. Открытый вопрос задачи закрыт ЗАМЕРОМ стандарта, не рассуждением: reference/02-schemas.md §7.1 и standard/07 §7.4.6 задают обязательные поля AR — tz-ref, verdict (findings-present|no-findings), status (draft|issued|superseded), produces-adapt, подпись. Замер копии живой БД: 63 таблицы, ни одна не имеет колонки verdict, ни один домен status не содержит issued; reviews несёт task_slug/run_type — по форме не AR. Признак = форма по §7.4.6 поверх artifact_classes из renar_tc_premise. Сложность medium подтверждена: несущих файлов пять (1 scripts + 3 tests + yaml). Файл 329 строк, запас есть.
- 2026-09-03T20:13:27Z [implementation] — ПОЧИНКА. AR_TABLE_CANDIDATES удалён; AR_SHAPE_FIELDS = (tz_ref, verdict, status) — обязательные поля записи AR по reference/02-schemas.md §7.1 / standard/07 §7.4.6 в написании субстрата (tz_ref уже так хранится на adapts). collect_state перебирает artifact_classes(conn) из renar_tc_premise (тени FTS исключены выводом): полная форма — AR-класс (issued суммируется по всем), частичная (есть tz_ref или verdict) — «почти-попадание» с перечнем недостающих полей в evidence; reviews объясняется замером — чего ей не хватает (tz_ref, verdict). Комментарий в модуле разводит «форма как ИДЕНТИЧНОСТЬ класса» и предостережение renar_tc_premise «колонка как ДОЛГ» (#491). Потребители в tests/: три фикстуры получили verdict, две ссылки на ar_table -> ar_tables, мутация {ar_table: None} -> {ar_tables: ()}. Четыре новых теста: неугаданное имя tz_review_verdicts найдено по форме; ar_records без verdict — названо и не засчитано; две AR-таблицы — обе названы, issued 3; поля формы транскрибированы из стандарта. Файл 380 строк (LF, как и был). mypy/ruff чисто после переименования локалов (have/lacks — cols/missing уже заняты ниже в той же функции). Замечено: renar conformance --write отдал старую строку probed — CLI исполняет развёрнутый профиль, регенерация только ПОСЛЕ bootstrap.
- 2026-09-03T20:16:25Z [implementation] — МУТАЦИИ 6/6 УБИТЫ (базовый прогон 26 passed, убитой считается только rc=1): M1 verdict не требуется -> 2 failed (no_verdict, class_absent: adapts стал бы AR); M2 возвращён поиск по имени -> unguessed_name красный; M3 issued не суммируется -> two_ar_tables; M4 почти-попадания сняты -> class_absent и no_verdict; M5 фильтр issued снят -> draft_only; M6 объяснение reviews снято -> class_absent. ЛОВУШКА, ПОЙМАНА НА СЕБЕ: первый прогон мутаций шёл с -p no:xdist при addopts -n — pytest падал с rc=4 «unrecognized arguments: -n», и «6/6 убито» было пустым; выявлено проверкой базового прогона той же командой. Харнесс мутаций обязан сначала показать rc=0 на оригинале и засчитывать только rc=1. CHANGELOG.md/.ru.md: новые записи под [Unreleased], синхронно.
- 2026-09-03T20:17:41Z [implementation] — bootstrap --ide all выполнен, RENAR-CONFORMANCE.yaml перегенерирован из нового измерителя (manifest v12): строки probed нет; evidence: «none of 30 artifact classes carries the §7.4.6 record shape (tz_ref, verdict, status); nearest: adapt_findings lacks verdict, status; adapt_interpretations lacks verdict, status; adapts lacks verdict; reviews lacks tz_ref, verdict, status». Замер: 63 таблицы в БД = 30 классов артефактов после исключения теней FTS и служебных. Память #542 (харнесс мутаций) и #543 (регенерация после bootstrap) записаны ДО done.
- 2026-09-03T20:18:07Z [implementation] — AC-1: ✓ tests/test_renar_clause_reactive_adapt.py::test_the_shape_is_the_standards_mandatory_record_fields (форма §7.4.6 поверх artifact_classes; AR_TABLE_CANDIDATES удалён; evidence называет признак и то, чего не хватает reviews; RENAR-CONFORMANCE.yaml v12 без probed). AC-2: ✓ tests/test_renar_clause_reactive_adapt.py::test_an_ar_table_under_an_unguessed_name_is_found_by_shape, tests/test_renar_clause_reactive_adapt.py::test_adversarial_review_class_absent_is_red (reviews lacks tz_ref, verdict), tests/test_renar_clause_reactive_adapt.py::test_a_table_with_a_tz_ref_but_no_verdict_is_named_and_not_counted, tests/test_renar_clause_reactive_adapt.py::test_collect_state_reddens_on_a_draft_only_ar_table, tests/test_renar_clause_reactive_adapt.py::test_two_ar_tables_are_both_named_and_their_issued_counts_summed; мутации 6/6 в журнале (базовый rc=0, убито только rc=1). AC-3: ✓ tests/test_renar_conformance.py::test_all_mandatory_fields_present и tests/test_renar_export.py (фикстуры с verdict); scoped 77 passed; ruff/mypy чисто; файл 380 строк. AC-4: ✓ CHANGELOG.md + CHANGELOG.ru.md синхронно; bootstrap --ide all выполнен, verify #2007 после него; память #542, #543 до done. Domain: AR под любым именем с полями tz_ref/verdict/status и строкой issued переводит под-проверку в зелёный; манифест публикует признак, а не догадку.
- 2026-09-26T19:02:59Z [done] — EVIDENCE-MOVED: tests/test_renar_clause_reactive_adapt.py::test_the_shape_is_the_standards_mandatory_record_fields => tests/test_renar_clause_reactive_adapt.py::test_the_shape_is_the_standards_scalar_mandatory_fields
