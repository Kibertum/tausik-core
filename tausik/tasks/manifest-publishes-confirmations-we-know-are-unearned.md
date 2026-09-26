---
slug: manifest-publishes-confirmations-we-know-are-unearned
title: "Манифест публикует ДВА подтверждения, чьи измерители мы сами знаем вырожденными: раскрыть до починки, а не молчать"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/renar_conformance.py"
  - "tests/test_renar_measurer_caveats.py"
  - "tests/test_renar_manifest_artifact.py"
scope_paths:
  - "scripts/renar_conformance.py"
  - "scripts/renar_measurer_caveats.py"
  - "tests/test_renar_measurer_caveats.py"
  - RENAR-CONFORMANCE.yaml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-31T17:36:14Z"
---

## Goal

НАЙДЕНО САМОРЕВЬЮ В #199, И НАЙДЕНО В СОБСТВЕННОЙ РАБОТЕ ЭТОЙ ЖЕ СМЕНЫ. Закоммитив RENAR-CONFORMANCE.yaml в корень, мы ОПУБЛИКОВАЛИ поля, о ложности которых знаем сами.

mandatory-clauses-confirmed печатает СЕМЬ подтверждений, и ДВА из них не заслужены:
  adapt-per-tz: true — §13.3.3 нарушено по ЧЕТЫРЁМ основаниям, замерено в этой же смене: AR как класса артефакта нет; наш единственный ADAPT стоит в draft при НЕПУСТЫХ backward findings, тогда как ветка «findings present» требует approved; подписей Архитектора ноль; у SPEC нет поля происхождения вообще — в таблице specs колонки source не существует. Измеритель — счёт adapts > 0 — не краснеет ни на одном из четырёх.
  spec-types-closed-list: true с evidence «9 closed SPEC types enforced» — §13.3.4 требует ОДИННАДЦАТЬ типов. Девять из одиннадцати подтверждением закрытого списка не являются.

ПОЧЕМУ ЭТО СРОЧНЕЕ САМОЙ ПОЧИНКИ. До этой смены манифеста не существовало, и ложное поле было внутренним дефектом. Теперь файл лежит в корне, объявлен читаемым снаружи, и мы сами написали в renar#47, что заводим его, чтобы наше состояние можно было прочесть. Опубликованное подтверждение, которое мы знаем неверным, — это ровно тот дефект, который вся смена и разбирала: значение печатается без права его печатать.

ЭТО НЕ ПОЧИНКА ИЗМЕРИТЕЛЕЙ, А РАСКРЫТИЕ. Обе починки — отдельные задачи и обе тяжелее: mandatory-clause-13-3-3-is-checked-by-counting-artifacts (упёрлась в гейт ёмкости в #199, budget 90 при остатке 84) и spec-closed-list-is-nine-while-the-standard-has-eleven (миграция схемы). Задача не подменяет их и не закрывает: она делает так, чтобы до их закрытия артефакт не врал молча.

ЧТО СДЕЛАТЬ. Ввести в манифест раздел, называющий КАЖДОЕ подтверждение, чей измеритель мы считаем недостоверным: имя положения, ЧЕМ измеряется сегодня, ПОЧЕМУ измеритель вырожден, slug открытой задачи. Раздел обязан быть виден читателю, а не спрятан в конец. Сослаться на него из шапки — там же, где уже сказано про журнал аудита.
ОБЯЗАТЕЛЬНАЯ ПРОВЕРКА: тест, который падает, если подтверждение объявлено недостоверным, а задачи с таким slug в базе НЕТ или она ЗАКРЫТА. Иначе раздел превратится в вечную отговорку — «оговорено» станет заменой «починено».

## Acceptance Criteria

AC-1 (раскрытие есть и оно машинно-читаемо): манифест несёт раздел measurer-caveats, называющий КАЖДОЕ недостоверное подтверждение четырьмя полями — clause, measured-as (чем меряется СЕГОДНЯ), why-degenerate (почему не краснеет), open-task (slug). Сегодня записей две: adapt-per-tz и spec-types-closed-list.

AC-2 (раскрытие видно ЧИТАТЕЛЮ, а не только парсеру): шапка манифеста называет раздел там же, где уже названы журнал аудита и способ прочесть прежние версии. Оговорка, лежащая ниже подтверждений, читается после них или не читается вовсе — то же правило, что применено к декларации несоответствия (память #475).

AC-3 (оговорка НЕ становится вечной отговоркой — негативный сценарий): тест ПАДАЕТ, если объявленная недостоверной запись ссылается на задачу, которой в базе НЕТ, либо на задачу в статусе done. Проверяется обеими ветвями: подставная запись с несуществующим slug обязана уронить тест; обе настоящие записи с открытыми задачами обязаны оставить его зелёным.

AC-4 (охрана пустого прогона): тест падает, если раздел measurer-caveats пуст или отсутствует, пока в нём есть чему быть. Пустой раздел и честный манифест не должны выглядеть одинаково.

AC-5 (граница ответственности объявлена): в самом разделе сказано, что он НЕ является исправлением и не заменяет закрытие названных задач. Проверяется наличием этой формулировки в выводе генератора.

AC-6 (регрессий нет): полная лента (добавляется тестовый файл — память #478), mypy, verify; закоммиченный манифест перевыпущен, тест на несвежесть зелёный.

## Plan

## Rollback

git revert одним коммитом; RENAR-CONFORMANCE.yaml перевыпускается командой tausik renar conformance --write. Откат возвращает манифест к состоянию БЕЗ раскрытия — то есть к худшему, но не сломанному: подтверждения остаются теми же, уходит только оговорка. Миграций схемы нет: раздел вычисляется, а не хранится в БД. Чужой корпус не трогается.

## Journal

- 2026-08-31T17:35:54Z [implementation] — AC-1 (раскрытие есть и машинно-читаемо, четыре поля на запись): ✓ tests/test_renar_measurer_caveats.py::test_every_caveat_is_fully_stated ✓ tests/test_renar_measurer_caveats.py::TestPublishedManifest::test_section_is_present_and_matches_the_registry ✓ verification_run #1925 AC-2 (раскрытие видно ЧИТАТЕЛЮ — шапка отправляет к разделу): ✓ tests/test_renar_measurer_caveats.py::TestPublishedManifest::test_header_points_the_reader_at_the_caveats ✓ verification_run #1925 AC-3 (оговорка не становится вечной отговоркой — обе ветви): ✓ tests/test_renar_measurer_caveats.py::test_named_task_exists_and_is_still_open ✓ verification_run #1925 AC-4 (охрана пустого прогона): ✓ tests/test_renar_measurer_caveats.py::test_registry_is_not_empty ✓ verification_run #1925 AC-5 (граница ответственности объявлена в самом разделе): ✓ tests/test_renar_measurer_caveats.py::test_disclaimer_refuses_to_be_mistaken_for_a_repair ✓ verification_run #1925 AC-6 (регрессий нет; манифест перевыпущен): ✓ tests/test_renar_manifest_artifact.py::test_committed_manifest_is_not_stale ✓ verification_run #1925 Domain: раздел читает ЧЕЛОВЕК СНАРУЖИ, открывший RENAR-CONFORMANCE.yaml. Проверка держит именно это: раздел присутствует в ЗАКОММИЧЕННОМ файле, его состав совпадает с реестром, каждая оговоренная статья ДЕЙСТВИТЕЛЬНО печатается в mandatory-clauses-confirmed (иначе оговорка — шум), и шапка отправляет к разделу до того, как читатель дойдёт до подтверждений. Negative: AC-3 обе ветви убиты. M16 — ссылка на несуществующую задачу, красное. M17 — ссылка на ЗАКРЫТУЮ задачу (подставлена задача этой же смены, закрытая час назад), красное. M20 обратная — подмена на ДРУГУЮ ОТКРЫТУЮ задачу, зелёное. AC-4: M18 опустошает реестр, красное. AC-5: M19 убирает из disclaimer фразу «not a repair», красное. ЗАЧЕМ ЗАДАЧА ВООБЩЕ ПОЯВИЛАСЬ: найдено САМОРЕВЬЮ собственной работы этой же смены. Закоммитив манифест в корень (задача conformance-manifest-is-absent...), мы превратили mandatory-clauses-confirmed в ОПУБЛИКОВАННОЕ утверждение, и два из семи true оказались незаслуженными. До публикации это был внутренний дефект; после — утверждение для всякого читающего, то есть ровно тот отказ, о котором вся смена: значение печатается без права. На этот раз печатали его МЫ, в файл, который сами попросили прочесть чужой трекер. ЧТО ЭТА ЗАДАЧА НЕ ДЕЛАЕТ, СКАЗАНО В САМОМ АРТЕФАКТЕ: измерители не чинит. Обе починки — открытые задачи и обе тяжелее (одна упёрлась в гейт ёмкости, другой нужна миграция схемы). ХРАПОВИК ПРОТИВ ПРЕВРАЩЕНИЯ ОГОВОРКИ В ПАРКОВКУ: запись обязана называть задачу, которая СУЩЕСТВУЕТ и ещё ОТКРЫТА. Закрытие починки автоматически роняет тест, пока оговорку не снимут тем же изменением. ЛИМИТ ФАЙЛА СОБЛЮДЁН ЧЕСТНО: renar_conformance.py уходил на 502 строки при блокирующем лимите 500. Реестр вынесен ОТДЕЛЬНЫМ модулем (это и архитектурно верно), а в самом файле сжата избыточность docstring — 499 строк, запас есть, на лимите не сидим. КРАСНЫЕ КОНТРОЛИ 5/5 УБИТЫ, RESTORE-FAIL 0, побочные эффекты сверены git status до/после (память #479) — дерево как до прогона. M19 СНАЧАЛА ДАЛА UNEXPECTED — дефект МУТАЦИИ, не теста: подменялся хвост строки, не затрагивавший проверяемых фраз. Перенацелена на то, что тест действительно утверждает. AC-6: полная лента 7602 passed, 24 skipped, 0 failed. mypy Success. Манифест перевыпущен, стал версией 2 с replaces: CFM-2026-08-31-tausik@v1 — цепь версий отработала на настоящем случае, а не в тесте.
- 2026-09-26T19:02:59Z [done] — EVIDENCE-MOVED: tests/test_renar_measurer_caveats.py::TestPublishedManifest::test_section_is_present_and_matches_the_registry => tests/test_renar_measurer_caveats.py::TestPublishedManifest::test_header_paragraph_matches_the_registry_state
- 2026-09-26T19:03:00Z [done] — EVIDENCE-MOVED: tests/test_renar_measurer_caveats.py::test_registry_is_not_empty => tests/test_renar_measurer_caveats.py::test_registry_is_either_populated_or_declared_empty
- 2026-09-26T19:04:15Z [done] — EVIDENCE-MOVED: tests/test_renar_measurer_caveats.py::TestPublishedManifest::test_header_paragraph_matches_the_registry_state => tests/test_renar_measurer_caveats.py::test_header_paragraph_matches_the_registry_state
- 2026-09-26T19:04:15Z [done] — EVIDENCE-MOVED: tests/test_renar_measurer_caveats.py::TestPublishedManifest::test_section_is_present_and_matches_the_registry => tests/test_renar_measurer_caveats.py::TestPublishedManifest::test_section_matches_the_registry_including_when_it_is_empty
