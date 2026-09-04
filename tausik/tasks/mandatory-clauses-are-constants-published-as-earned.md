---
slug: mandatory-clauses-are-constants-published-as-earned
title: "Пять из семи обязательных положений манифеста — константы, а шапка публикует, что всякое true заслужено"
status: active
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/renar_conformance.py (вынос и подключение), новые scripts/renar_mandatory_clauses.py и scripts/renar_clause_closed_lists.py, scripts/renar_measurer_caveats.py (реестр), scripts/renar_tc_premise.py (basis/premise), tests/test_renar_conformance.py, tests/test_renar_measurer_caveats.py, новые tests/test_renar_mandatory_clauses.py и tests/test_renar_clause_closed_lists.py, RENAR-CONFORMANCE.yaml (регенерация), CHANGELOG.md, CHANGELOG.ru.md, docs/en|ru упоминания блока манифеста"
scope_exclude: "состав SPEC_TYPES, FINDING_CATEGORIES и статусов ADAPT (не меняются); renar_clause_reactive_adapt.py (§13.3.3 готова); gate_registry.py; схема БД и миграции"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЗВАНО СВЕРКОЙ SENAR 9.5 КАК HIGH И ДО СИХ ПОР НЕ ЗАВЕДЕНО; ЗАВОДИТСЯ ИЗ db-gated-ratchets-never-run-in-ci, ГДЕ ПОТРЕБОВАЛОСЬ ЧЕСТНО ОТВЕТИТЬ, ЧТО ИМЕННО ДЕРЖИТ ОГОВОРКУ tc-pos-neg-pairing ПОСЛЕ ЗАКРЫТИЯ CI-РАЗРЫВА.

ИЗМЕРЕНО ЧТЕНИЕМ eval_mandatory_clauses (scripts/renar_conformance.py:214). Обязательных положений СЕМЬ. Выводятся из замера ТРИ: substrate-v1-v6 (из сигнала), adapt-per-tz (bundle clause_13_3_3, именованные подпроверки), tc-pos-neg-pairing (bundle clause_13_3_5). Являются КОНСТАНТАМИ ПЯТЬ: sot-inversion, spec-types-closed-list, quality-gates-closed-list, closed-lists-backward-findings — литеральный True прямо в словаре, — и tc-pos-neg-pairing, который выведен синтаксически, но pairing_clause() НЕ ПРИНИМАЕТ АРГУМЕНТА и возвращает честную константу.

ПОЧЕМУ ЭТО ДЕФЕКТ, А НЕ УСТРОЙСТВО. Константа сама по себе не ложь: §13.3.5 действительно вакуумна, пока в проекте нет класса TC, и это записано в коде честно. Дефект в РАЗРЫВЕ МЕЖДУ КОНСТАНТОЙ И ТЕМ, ЧТО О НЕЙ ПУБЛИКУЕТСЯ. Шапка манифеста сообщает наружу, что всякое true заслужено, а пять из семи true не могут ПОКРАСНЕТЬ НИ НА ОДНОМ нарушении: у трёх из них (spec-types-closed-list, quality-gates-closed-list, closed-lists-backward-findings) поле evidence называет счёт или перечень, из чего читается, что проверка была, — а confirmed при этом литерал, который не зависит от этого счёта. Ровно этот класс дефекта уже дважды чинили в #200 и #202 поштучно: §13.3.3 подтверждалась счётом «ADAPT больше нуля» и была зелёной при четырёх нарушениях, §13.3.5 краснела на чужой обязанности. Оба раза чинили ОДНУ клаузу; общий вопрос «сколько ещё таких» не задавался.

ЧТО ТРЕБУЕТСЯ, И ЧЕГО НЕ ТРЕБУЕТСЯ. НЕ требуется превратить все пять в измерители любой ценой: у вакуумной клаузы измерять нечего, и выдуманный измеритель хуже честной константы. Требуется, чтобы КАЖДАЯ константа была: (1) названа константой в публикуемом артефакте, а не выдана за измеренную; (2) снабжена ХРАПОВИКОМ, который краснеет, когда предпосылка вакуумности перестаёт держаться, — по образцу renar_tc_premise, где такой храповик уже есть и уже работает; (3) либо, если предмет измерим, выведена из замера. Разобрать по одной, с решением на каждую и с основанием.

НАЧИНАТЬ С ЗАМЕРА, НЕ С ПРАВКИ. Для каждой из пяти проверить МУТАЦИЕЙ, способна ли она покраснеть хоть на чём-нибудь: подложить состояние, нарушающее положение, и посмотреть на confirmed. Предъявить таблицей: клауза, чем подтверждается сегодня, красная ветвь есть или нет, что показала мутация. Без этой таблицы разговор о «пяти литеральных True» остаётся пересказом, а не замером — и предпосылка «положение вакуумно» у каждой из пяти обязана быть проверена ОТДЕЛЬНО, потому что у §13.3.5 она держится, а у §13.3.1 (sot-inversion) предмет живой и вакуумности нет вовсе.

СЦЕПКА, КОТОРУЮ НАДО ЗНАТЬ. Оговорка tc-pos-neg-pairing в MEASURER_CAVEATS указывает open-task СЮДА. Храповик test_named_task_exists_and_is_still_open требует, чтобы задача была открыта, и с #203 он выполняется в любой выгрузке, включая CI. Значит закрыть эту задачу можно, только сняв оговорку по существу или перенаправив её на следующую открытую работу — молча удалить не выйдет, машина не даст.

## Acceptance Criteria

AC-1 (таблица замера ДО правки): для каждой из пяти констант в журнале задачи — клауза, чем подтверждается сегодня, есть ли красная ветвь, что показала мутация (подложенное нарушающее состояние БД или объявления, и confirmed при нём). Таблица снята прогоном по временным БД, не пересказом.
AC-2 (§13.3.4 spec-types-closed-list ВЫВОДИТСЯ из замера): подпроверки — живой CHECK на specs.type допускает ровно объявленный закрытый список SPEC_TYPES (сверка через sqlite_master, без второго литерального перечня), и ни одна строка specs не несёт тип вне списка. Negative: БД, чей CHECK допускает локальный тип FOO (или не имеет CHECK), и БД со строкой типа вне списка — клауза false с названной подпроверкой (тесты, мутации).
AC-3 (§13.3.7 closed-lists-backward-findings ВЫВОДИТСЯ из замера): те же две подпроверки над adapt_findings.category против FINDING_CATEGORIES, плюс закрытый список статусов ADAPT (adapts.status CHECK против объявленного перечня v50). Negative: CHECK с восьмой категорией или строка вне списка — false (тесты, мутации).
AC-4 (§13.3.6 quality-gates-closed-list ВЫВОДИТСЯ из объявления): блок quality-gates манифеста становится объявлением-литералом в одном месте, а клауза вычисляется из него: ровно пять id закрытого списка, qg-0..qg-2 = required, qg-3/qg-4 ∈ {required, declared, absent}. Negative: объявление с qg-5, с qg-0 = declared или без qg-4 — false (тесты на чистой функции, мутации).
AC-5 (константы НАЗВАНЫ константами в артефакте): манифест публикует рядом с mandatory-clauses-confirmed блок mandatory-clauses-basis с основанием каждой клаузы из закрытого перечня {measured, machinery, vacuous}; для machinery (sot-inversion, substrate-v1-v6) и vacuous (tc-pos-neg-pairing) названо, чем держится предпосылка (premise-watched-by). Шапка манифеста перестаёт утверждать «всякое true заслужено» безусловно и отсылает к basis. Тест: у каждой клаузы basis из закрытого перечня; у каждой не-measured клаузы назван храповик; measured клаузы имеют красную ветвь (мутация состояния даёт false).
AC-6 (храповик предпосылки для machinery): тест в репозитории краснеет, если в эффективной конфигурации verify-first снят или перестал быть блокирующим либо хук «задача до кода» не развёрнут; для vacuous — существующий renar_tc_premise.classes_appeared назван в артефакте.
AC-7 (оговорка tc-pos-neg-pairing снята ПО СУЩЕСТВУ или перенаправлена): реестр MEASURER_CAVEATS либо опустошён с REGISTRY_EMPTIED_BY = эта задача (тесты реестра зелёные, шапка меняется на форму «пусто»), либо оговорка перенаправлена на следующую открытую работу с обоснованием в журнале. Negative: тест реестра краснеет при пустом реестре без названия опустошившей задачи (существующий).
AC-8: renar_conformance.py остаётся ≤ 500 строк (вынос eval_mandatory_clauses и подпроверок закрытых перечней в отдельные модули); порядок регенерации манифеста соблюдён (правка → тесты → bootstrap --ide all → --check → conformance --write); test_committed_manifest_is_not_stale зелёный; CHANGELOG в обоих файлах; мутации объявлены и убиты по ветви; docs, называющие measurer-caveats или блок mandatory-clauses, приведены в соответствие.

## Plan

## Rollback

git revert коммита задачи; манифест вернётся к v17 следующей регенерацией (журнал версий не переиспользуется — новая версия поверх). Схема БД и данные не затрагиваются.

## Journal

- 2026-09-04T21:45:20Z [implementation] — ТАБЛИЦА ЗАМЕРА (AC-1), снята ПРОГОНОМ по временным БД (SQLiteBackend + DDL-подмена CHECK), скрипт в scratchpad, удалён после. Формат: клауза | чем подтверждается сегодня | красная ветвь | мутация → confirmed. (1) sot-inversion §13.3.1 | литерал True, evidence «QG-0 task-before-code + QG-2 verify-first policy enforced» | НЕТ | пустая БД → True; bundle, где единственный сигнал substrate_v1_v6=False и никаких QG-сигналов → True. Не зависит ни от БД, ни от сигналов. (2) spec-types-closed-list §13.3.4 | литерал True, evidence «closed at len(SPEC_TYPES) (service + DB CHECK)» — evidence НАЗЫВАЕТ DB CHECK, но код его НЕ ЧИТАЕТ | НЕТ | CHECK specs.type допускает локальный тип FOO и строка типа FOO существует → True; CHECK без DOC (десять вместо одиннадцати) → True. (3) closed-lists-backward-findings §13.3.7 | литерал True, evidence «closed at len(FINDING_CATEGORIES)» | НЕТ | CHECK adapt_findings.category с восьмой категорией vibes и находка в ней → True; adapts.status CHECK с локальным статусом signed → True. (4) quality-gates-closed-list §13.3.6 | литерал True, evidence «QG-0/QG-2 task-lifecycle gates (closed list)» | НЕТ | манифест объявляет qg-5 и qg-0=absent → True (клауза не читает блок quality-gates вовсе; блок — литерал в build_manifest). (5) tc-pos-neg-pairing §13.3.5 | pairing_clause() без аргумента, честная константа с оговоркой | НЕТ (по решению #202) | таблица spec_tests с positive TC без negative → True. КОНТРОЛЬ: adapt-per-tz на пустой БД → False — измеритель, умеющий краснеть, отличим. ПРЕДПОСЫЛКА ВАКУУМНОСТИ ПРОВЕРЕНА ОТДЕЛЬНО: (1) — предмет ЖИВОЙ (три SPEC, задачи), вакуумности нет; нарушения, названные §13.3.1 (reverse-engineering SR из кода, тихая адаптация SR), требуют класса SR, которого нет; положительная обязанность держится машинерией QG-0/QG-2 → basis machinery с храповиком на включённость. (2),(3) — предмет живой и ИЗМЕРИМ по схеме: CHECK читается из sqlite_master → measured. (4) — предмет есть: наше собственное объявление quality-gates; измерим над объявлением → basis declared с красной ветвью. (5) — вакуумна (TC-класса нет), храповик renar_tc_premise.classes_appeared есть → basis vacuous; оговорка снимается по существу, потому что артефакт перестаёт публиковать true как заслуженное. НАХОДКА ВНЕ ОБЛАСТИ (предъявить владельцу): §13.3.7 третий пункт — закрытый список состояний жизненного цикла главы 10 (draft/approved/verified/accepted/deprecated); наш specs.status CHECK = draft/active/deprecated, расходится со стандартом. В эту задачу не беру (состав перечней исключён из scope), подпроверка по statuses строится только на ADAPT_STATUSES (v50).
