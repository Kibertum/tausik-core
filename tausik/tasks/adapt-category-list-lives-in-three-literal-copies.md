---
slug: adapt-category-list-lives-in-three-literal-copies
title: "Закрытый список категорий находок ADAPT лежит в трёх литеральных копиях плюс перечислением в прозе MCP"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 110
defect_of: null
scope: "scripts/service_adapts.py (источник, не меняется), scripts/renar_clause_reactive_adapt.py, scripts/project_parser_adapts.py, harness/claude/mcp/project/tools_adapt.py, tests/closed_list_counts.py, tests/test_spec_types_closed_list.py, tests/test_adapts.py, tests/test_renar_clause_reactive_adapt.py, tests/test_enum_single_source.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "СОСТАВ перечней (семь категорий, статусы, типы SPEC) — не меняется; scripts/backend_schema_adapts.py и scripts/backend_migrations_v36.py (каноническое DDL и историческая миграция остаются SQL-литералами); четыре категории Shared Brain (решение #256, вне релиза)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - adapt-finding-categories-count-is-written-not-derived
completed_at: null
---

## Goal

НАЙДЕНО ИНВЕНТАРЁМ В СМЕНЕ #201 ПРИ РАБОТЕ НАД adapt-finding-categories-count-is-written-not-derived, ЗАМЕРЕНО ЧТЕНИЕМ ИСХОДНИКОВ, НЕ ПРЕДПОЛОЖЕНО. Заведено ОТДЕЛЬНО СОЗНАТЕЛЬНО, а не приклеено к задаче про счёт: это дефект ДРУГОГО КЛАССА (второй литеральный список против написанного числа) и по объёму равен всей spec-closed-list-is-nine-while-the-standard-has-eleven, которая в #200 закрылась с отметкой COMPLEXITY UNDERSTATED и call_actual=110 против budget=60. Слипание повторило бы ту ошибку буквально.

ЗАМЕР. Закрытый перечень категорий обратных находок (§7.4.4, семь значений) существует в ЧЕТЫРЁХ независимых представлениях плюс схема:
1. scripts/service_adapts.py:28 FINDING_CATEGORIES — кортеж, де-факто источник;
2. scripts/renar_clause_reactive_adapt.py:43 BACKWARD_FINDING_CATEGORIES — СВОЙ кортеж с теми же семью строками, объявленный заново, а не импортированный. Введён в #200 задачей про §13.3.3, то есть копия сделана НЕДЕЛЮ НАЗАД и прошла ревью;
3. harness/claude/mcp/project/tools_adapt.py:11 _FINDING_CATEGORIES — список для enum схемы инструмента MCP;
4. harness/claude/mcp/project/tools_adapt.py:65 — те же семь имён ЕЩЁ РАЗ, перечисленные ПРОЗОЙ внутри description инструмента: «(contradiction/gap/hidden-assumption/feasibility/regulatory/terminology/scope)». Это представление читают агенты, и оно не связано с enum ничем, кроме внимательности автора;
5. CHECK на adapt_findings.category в схеме БД.

ОСОБО: докстринг harness/claude/mcp/project/tools_adapt.py:5 УТВЕРЖДАЕТ «No mirror to keep in sync: harness/claude/mcp is the single canonical tree», держа при этом зеркало константы сервиса. Утверждение верно про ДЕРЕВО (MCP не копируется по IDE) и ложно про КОНСТАНТУ. Это ровно тот класс, что разбирала renar-debt: строка утверждает о себе больше, чем заслужила.

ПОЧЕМУ ЭТО ДЕФЕКТ, ХОТЯ ВСЕ ЧЕТЫРЕ КОПИИ СЕЙЧАС СОВПАДАЮТ. Совпадение — не свойство конструкции, а состояние. Ровно так же выглядел список типов SPEC до ADR-013: пять мест, все согласованные, до дня, когда стандарт сдвинулся, и тогда разошлись все пять поодиночке. §7.4.4 — норма ВНЕШНЯЯ, мы её не контролируем.

ПРЕЦЕДЕНТ И ГОТОВЫЙ ПРИЁМ, НЕ НАДО ИЗОБРЕТАТЬ. spec-closed-list в #200 свела пять мест в одно: модуль MCP стал ЧИТАТЬ константу вместо зеркала, число форматируется из len(), детектор второго литерального перечня (LIST_RE в tests/test_spec_types_closed_list.py) краснеет на второй копии. Здесь тот же ход, и LIST_RE надо ОБОБЩИТЬ на категории находок, а не копировать: копия детектора есть тот же дефект уровнем выше. В смене #201 LIST_RE был намеренно оставлен суженным до типов SPEC, и причина записана прямо в тесте.

ЧТО ПРОВЕРИТЬ ПРИ ПЛАНИРОВАНИИ И ЧЕГО НЕ РАЗРЕЗАТЬ. Перечисление прозой в description MCP снять НЕЛЬЗЯ молча — это то, по чему агент выбирает категорию; его надо СОБИРАТЬ из константы, а не удалять. Импорт service_adapts в renar_clause_reactive_adapt проверить на цикл: renar_clause_reactive_adapt уже импортируется из renar_conformance. Состав списка и статусы ADAPT не трогать — статусы разбирает adapt-status-enum-diverged-from-the-standards-closed-list.

## Acceptance Criteria

AC-1 (инвентарь предъявлен цифрами до правки): в журнале задачи перечислены ВСЕ литеральные носители семи значений с путями и строками, снятые обходом ПО ЗНАЧЕНИЮ, ПО ВЫЗОВУ и ПО СХЕМЕ, включая носитель, которого нет в тексте задачи (scripts/project_parser_adapts.py). Для каждого сказано: источник, производное, историческое или каноническое DDL.
AC-2 (копий в коде не остаётся): renar_clause_reactive_adapt, project_parser_adapts и harness/claude/mcp/project/tools_adapt читают FINDING_CATEGORIES из service_adapts, а не объявляют свой кортеж; проза описания инструмента MCP собирается из константы (число из len(), значения из join) и НЕ удаляется — по ней агент выбирает категорию.
AC-3 (детектор второй копии ОБОБЩЁН, а не скопирован): матчер литерального перечня живёт в tests/closed_list_counts.py, параметризован значениями закрытого перечня и ВЫВЕДЕН из них (никакой альтернативы имён руками); test_spec_types_closed_list использует его же, поведение для типов SPEC не меняется. Negative: подложенная четвёрка подряд идущих кавычечных значений категорий даёт находку с путём файла; подложенная четвёрка типов SPEC — по-прежнему даёт.
AC-4 (разрешающий список честен): каждый оставшийся литерал объявлен с причиной из двух допустимых классов — источник/каноническое DDL или исторический носитель (миграция, транскрипция стандарта в тесте). Ни одна запись не добавлена, чтобы заглушить живое утверждение.
AC-5 (докстринг перестаёт переобещать): фраза tools_adapt «No mirror to keep in sync» исправлена — она верна про дерево и была ложна про константу; та же поправка в докстринге tests/test_enum_single_source, где сказано, что схемы MCP держат литералы.
AC-6 (охрана единственного источника расширена на категории): tests/test_enum_single_source покрывает категории так же, как статусы и типы; композиция семи значений пиньтся ОДНИМ тестом (транскрипция стандарта), остальные проверяют тождество с источником.
AC-7: полный прогон ленты, bootstrap --ide all и --check без дрейфа, mypy и ruff чисто, файлы в пределах 500 строк; мутации объявлены и убиты ПО ВЕТВИ либо объявлены эквивалентными с доказательством; CHANGELOG в обоих файлах.

## Plan

## Rollback

git revert коммита задачи; схема БД и данные не затрагиваются, значения перечней не меняются, поэтому откат не требует миграции.

## Journal

- 2026-09-06T11:35:46Z [planning] — ИНВЕНТАРЬ ДО ОЦЕНКИ (AC-1), снят ПО ЗНАЧЕНИЮ (grep 'contradiction' по scripts/harness/tests/docs/bootstrap), ПО ВЫЗОВУ (FINDING_CATEGORIES) и ПО СХЕМЕ (category TEXT CHECK). ЛИТЕРАЛЬНЫХ НОСИТЕЛЕЙ СЕМИ ЗНАЧЕНИЙ ШЕСТЬ, а не три: (1) scripts/service_adapts.py:30 FINDING_CATEGORIES — ИСТОЧНИК. (2) scripts/renar_clause_reactive_adapt.py:45 BACKWARD_FINDING_CATEGORIES — копия, названа в задаче. (3) scripts/project_parser_adapts.py:14 FINDING_CATEGORY_CHOICES — КОПИЯ, В ЗАДАЧЕ НЕ НАЗВАНА. Особо: в ТОМ ЖЕ файле ADAPT_STATUS_CHOICES = list(ADAPT_STATUSES) с комментарием «Derived from the service-layer source of truth (no independent literal here)» — то есть приём применён к статусам и не применён к категориям. (4) harness/claude/mcp/project/tools_adapt.py:11 _FINDING_CATEGORIES — копия, названа. (5) scripts/backend_schema_adapts.py:55 — каноническое DDL (SQL, интерполировать нельзя) — остаётся. (6) scripts/backend_migrations_v36.py:47 — историческая миграция — остаётся. Плюс транскрипции стандарта в тестах: tests/test_adapts.py:70 (пинит состав) и tests/test_renar_clause_reactive_adapt.py:390. ПОПРАВКА К ЗАМЕРУ ЗАДАЧИ: пункт (4) её текста — «те же семь имён ЕЩЁ РАЗ прозой в description» — УСТАРЕЛ: проза уже собирается из локальной копии (f"{len(_FINDING_CATEGORIES)}" и '/'.join(_FINDING_CATEGORIES), строки 82-83). Дефект не в прозе, а в том, что она наследует дрейф ЗЕРКАЛА. ПРЕЦЕДЕНТ ИЗМЕРЕН, А НЕ ПРЕДПОЛОЖЕН: harness/claude/mcp/project/tools_spec.py в #200 уже решил ровно это — кладёт scripts на sys.path (с разбором развёрнутого layout в комментарии) и импортирует service_specs; его докстринг прямо говорит: «A mirror pinned by a test is still a second literal that has to be edited in lockstep, and the standard just moved under it». Значит для tools_adapt приём готов и проверен. РАСХОЖДЕНИЕ ДОКСТРИНГОВ: tools_adapt утверждает «No mirror to keep in sync: harness/claude/mcp is the single canonical tree» (верно про ДЕРЕВО, ложно про КОНСТАНТУ), а tests/test_enum_single_source утверждает «The MCP schemas keep literal lists (a JSON schema should be self-contained)» — что уже ложно для tools_spec. СТАТУСЫ В tools_adapt: _ADAPT_STATUSES тоже литерал, пиньется тестом. Задача исключала статусы, потому что их СОСТАВ разбирала adapt-status-enum-diverged-from-the-standards-closed-list — она ЗАКРЫТА (v50), состав вопрос закрыт. Зеркало же есть предмет ИМЕННО ЭТОЙ задачи, и оставлять его в том же файле — половина починки; беру, объявляя расширение области здесь. ДЕТЕКТОР: счётчик написанного числа в tests/closed_list_counts.py УЖЕ параметризован (ClosedList: SPEC_TYPE_LIST и ADAPT_FINDING_CATEGORY_LIST). Не обобщён именно LIST_RE — детектор второй литеральной копии, живущий в test_spec_types_closed_list.py альтернативой имён РУКАМИ (его пришлось править руками, когда ADR-013 добавил два типа). Обобщаю в ClosedList.literal_list_re(), выводя из values. СЛОЖНОСТЬ ПОСЛЕ ИНВЕНТАРЯ: остаётся complex — носителей шесть вместо трёх, плюс обобщение детектора и две поправки докстрингов.
