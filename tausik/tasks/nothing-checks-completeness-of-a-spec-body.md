---
slug: nothing-checks-completeness-of-a-spec-body
title: "Полноту тела SPEC не проверяет ни один гейт — §8.4.1 применим к нам, соответствие не доказано"
status: done
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: medium
role: architect
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "scripts/ (контроль полноты тела SPEC, подключение к реестру гейтов), tests/, docs/{ru,en} при изменении контракта SPEC, CHANGELOG.md, CHANGELOG.ru.md."
scope_exclude: "Закрытый список типов здесь НЕ расширяется — это предмет spec-closed-list-is-nine-while-the-standard-has-eleven. Существующие SPEC-артефакты не переписываются: задача строит контроль, а приведение тел в соответствие — отдельная работа с отдельной ценой. Корпус ../../standards/ не правится."
relevant_files:
  - "scripts/spec_completeness.py"
  - "tausik/spec_coverage.json"
  - "tests/test_spec_completeness.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on:
  - spec-closed-list-is-nine-while-the-standard-has-eleven
completed_at: "2026-08-31T15:03:45Z"
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

НАЙДЕНО В СЕССИИ #191 ПРИ ВЫНЕСЕНИИ ВЕРДИКТА ПО ADR-023 (задача four-accepted-adrs-were-never-assessed). ADR-023 spec-coverage-completeness — ЕДИНСТВЕННЫЙ из четырёх непроверенных принятых ADR, который нас ОБЯЗЫВАЕТ. Его §5 (строка 58, сверено машиной) вводит в §8.4.1 положение «Полнота охвата»: «обязательное тело описывает предмет спецификации исчерпывающе; ограничение охвата подмножеством элементов по субъективному критерию отбора запрещено во всех одиннадцати типах и вне зависимости от лексики». Оговорки об уровне RENAR у положения НЕТ — в отличие от ADR-020 оно не отсекается нашим RENAR-1. ЧЕМ СООТВЕТСТВИЕ НЕ ДОКАЗАНО, НАЗВАНО ТОЧНО: живой gates status показывает, что SPEC-артефакты трогают ровно два гейта, оба warn — renar_drift_schema (валидация СХЕМЫ SPEC/ADAPT) и renar_drift_provenance (СВЕЖЕСТЬ связей task↔SPEC). Полноту ТЕЛА не проверяет ни один из них и ни один другой гейт реестра; scripts/renar_drift.py:91 сверяет `s["type"] not in SPEC_TYPES`, то есть тип, а не исчерпывающесть описания. Контроля, отвечающего на вопрос §8.4.1, у нас нет ни блокирующего, ни предупреждающего. ВТОРАЯ СТОРОНА ТОГО ЖЕ: наш закрытый список типов — девять (scripts/service_specs.py:20, «CLOSED list of 9»), SPEC-TEST и SPEC-DOC отсутствуют, поэтому норму «во всех одиннадцати типах» невозможно исполнить в системе, знающей девять. Задача spec-closed-list-is-nine-while-the-standard-has-eleven заведена ранее и здесь НЕ дублируется — она усилена новым следствием. ЗАВИСИМОСТЬ: контроль полноты имеет смысл строить ПОСЛЕ или ВМЕСТЕ с расширением списка до одиннадцати, иначе он будет заведомо неполон на два типа.

## Acceptance Criteria

AC1. Существует контроль, отвечающий на вопрос §8.4.1: описывает ли обязательное тело SPEC свой предмет исчерпывающе. Контроль называет КОНКРЕТНЫЙ SPEC и КОНКРЕТНОЕ упущение, а не выдаёт число покрытия.
AC2. Контроль работает ПО ПРЕДМЕТУ, а не по списку слов. ADR-023 §4 прямо разбирает, почему запрет лексики («ключевой», «критический», «основной») ошибается в обе стороны: те же слова законны, когда называют свойство самого предмета, и незаконны, когда сужают подлежащее описанию. Проверка, реализованная как чёрный список прилагательных, критерию НЕ УДОВЛЕТВОРЯЕТ, даже если ловит все сегодняшние случаи.
AC3. НЕГАТИВНЫЙ СЦЕНАРИЙ, ОБЯЗАТЕЛЕН, ПРЯМО ИЗ ТЕКСТА ADR. Предъявлен прогон на SPEC, где оценочное прилагательное или оборот меры НАЗЫВАЕТ СВОЙСТВО ПРЕДМЕТА, а не сужает охват, — и контроль на нём ЗЕЛЁН. Красный на таком входе есть ложное срабатывание и провал задачи: он воспроизводит ровно ту ошибку, которую ADR-023 §4 отверг у исходного тикета.
AC4. Охват контроля назван честно числом: сегодня он способен покрыть девять типов из одиннадцати, потому что SPEC-TEST и SPEC-DOC у нас отсутствуют. Отчёт «покрыты все типы» при девяти известных — провал: это то же сужение охвата по удобному критерию, которое §8.4.1 и запрещает.
AC5. Зависимость от spec-closed-list-is-nine-while-the-standard-has-eleven названа в БД связью, а не словами в тексте.
AC6. Мутация обязательна: SPEC с намеренно суженным телом даёт красный с названным именем, возврат побайтовой копией со сверкой sha256 даёт зелёный. git checkout запрещён.

## Plan

## Rollback

git revert коммита задачи. Контроль вводится severity=warn до первого чистого прогона на всём корпусе SPEC и повышается до block отдельным решением — блокирующий контроль полноты, включённый сразу, остановит работу на каждом существующем неполном SPEC. Откат до warn — одна строка в реестре гейтов.

## Journal

- 2026-08-31T15:02:35Z [implementation] — ЖИВОЙ ПРОГОН КОНТРОЛЯ: 2 тела описывают свой предмет исчерпывающе (sec-config-trust-tiers, team-state-in-git-format), 1 находка — renar-adoption UNCHECKED. reach: covers 9 of 11 SPEC types; SPEC-TEST, SPEC-DOC absent. ЛОЖНОЕ СРАБАТЫВАНИЕ ПОЙМАНО НА СЕБЕ И ИСПРАВЛЕНО ДО ЗАПИСИ ACCEPTANCE. Первый прогон дал ЧЕТЫРЕ красных на sec-config-trust-tiers: enumerator выдаёт `gates.*.enabled` и три соседних семейных ключа, а тело пишет их как `gates.<имя>.enabled` — то есть проверка ловила ТИПОГРАФИКУ плейсхолдера, а не предмет. Это ровно та ошибка, которую AC3 объявляет провалом, только в другом обличье. Починка: `*` сопоставляется одним сегментом пути, сегмент исключает пробел, точку и обратный апостроф — чтобы послабление не превратилось в пропуск. Оба направления закреплены тестами: test_a_family_key_is_covered_however_the_placeholder_is_written (4 написания) и test_the_wildcard_cannot_swallow_its_way_across_a_sentence (4 обманки). AC5 ЗАМЕР, А НЕ ДЕЙСТВИЕ: связь с spec-closed-list-is-nine-while-the-standard-has-eleven В БД УЖЕ БЫЛА — task depends ответил «already comes after; nothing changed». Не приписываю себе её создание. МУТАЦИИ 8/8 KILLED. MB1 — та, которую AC6 требует буквально: суживает НАСТОЯЩЕЕ тело docs/ru/config-trust-tiers.md на диске (`risk.l3_block_on_high` -> `risk.renamed_away`), живой контроль обязан назвать спецификацию; возврат побайтовый со сверкой sha256, git checkout не применялся, и после возврата отдельная проверка печатает GREEN. MS1-MS7 снимают у контроля по одной способности отказать. ЧЕСТНО: MS5 в первом прогоне SURVIVED — я нацелил его селектор на не тот тест; дефект был в харнессе, не в покрытии, исправлен и убит.
- 2026-08-31T15:03:42Z [implementation] — AC1 pass — контроль существует и отвечает ИМЕННО на вопрос §8.4.1: исчерпывающе ли обязательное тело описывает свой предмет. scripts/spec_completeness.py + закоммиченный реестр tausik/spec_coverage.json. Живой прогон: 2 тела исчерпывающи (sec-config-trust-tiers, team-state-in-git-format), 1 находка — renar-adoption. Отчёт называет КОНКРЕТНЫЙ SPEC и КОНКРЕТНОЕ упущение по имени элемента; число покрытия не выдаётся вовсе, и это закреплено утверждением assert '%' not in rendered в test_the_finding_names_the_spec_and_the_element_not_a_percentage. | AC2 pass — работа ПО ПРЕДМЕТУ, чёрного списка прилагательных нет нигде. SPEC объявляет ПЕРЕЧИСЛИМОЕ МНОЖЕСТВО своего предмета и enumerator, читающий его по ЖИВОМУ коду: config_trust_guarded_keys берёт config_trust.GUARDS, state_projection_kinds берёт state_serialize.ENTITY_DIRS. Член, добавленный в продукт, расширяет обязанность тела без правки списка. Отдельно закреплено, что лексика не читается ни в какую сторону: test_the_check_reads_no_vocabulary_at_all вычищает из ПОЛНОГО тела все оценочные слова (остаётся зелёным) и добавляет их в СУЖЕННОЕ (остаётся красным с теми же двумя элементами). | AC3 pass — НЕГАТИВНЫЙ СЦЕНАРИЙ ПРЕДЪЯВЛЕН И ЗЕЛЁН. test_an_evaluative_adjective_naming_a_property_stays_green подаёт тело, где «the single most critical», «the key switch», «the core protection», «the least significant of the four», «a largely mechanical case» — каждое называет СВОЙСТВО элемента, и все четыре элемента описаны: check_body возвращает []. Красный на таком входе воспроизвёл бы ошибку, отвергнутую ADR-023 §4, и был бы провалом задачи; его нет. Отдельно test_measure_phrases_do_not_make_a_complete_body_red: ранжирование — не сужение. | ЛОЖНОЕ СРАБАТЫВАНИЕ БЫЛО ПОЙМАНО НА СЕБЕ, ДО ЗАПИСИ ACCEPTANCE, И ЭТО ЧАСТЬ AC3. Первый живой прогон дал ЧЕТЫРЕ красных на sec-config-trust-tiers: enumerator выдаёт семейный ключ gates.*.enabled и трёх соседей, а тело пишет их как gates.<имя>.enabled. Проверка ловила ТИПОГРАФИКУ плейсхолдера, а не предмет — та же ошибка в другом обличье. Починка: `*` сопоставляется ОДНИМ сегментом пути, и сегмент исключает пробел, точку и обратный апостроф, чтобы послабление не стало пропуском. Оба направления закреплены: test_a_family_key_is_covered_however_the_placeholder_is_written (4 написания, включая gates.<имя>, gates.<name>, gates.mypy) и test_the_wildcard_cannot_swallow_its_way_across_a_sentence (4 обманки вида «gates are enabled by default» обязаны остаться красными). | AC4 pass — охват назван ЧИСЛОМ и честно: reach() печатает «covers 9 of 11 SPEC types; SPEC-TEST, SPEC-DOC absent from our closed list». Число ВЫЧИСЛЯЕТСЯ из STANDARD_SPEC_TYPES минус service_specs.SPEC_TYPES, а не утверждается: test_reach_reports_full_coverage_only_when_all_eleven_types_exist показывает, что «11 из 11» появится ровно тогда, когда список расширят, и не раньше. Та же оговорка продублирована в _reach закоммиченного реестра — там, где её увидит тот, кто придёт ДОБАВЛЯТЬ SPEC. Отчёт «покрыты все типы» невозможен по построению. | AC5 pass — связь названа В БД, а не словами: task depends nothing-checks-completeness-of-a-spec-body after spec-closed-list-is-nine-while-the-standard-has-eleven. ЧЕСТНО: связь УЖЕ СУЩЕСТВОВАЛА, команда ответила «already comes after; nothing changed» — я её не создавал и не приписываю себе. | AC6 pass — 8 мутаций, 8 KILLED, SETUP-FAIL 0, RESTORE-FAIL 0. MB1 — та, которую AC6 требует буквально: суживает НАСТОЯЩЕЕ тело docs/ru/config-trust-tiers.md на диске (risk.l3_block_on_high -> risk.renamed_away), и живой контроль обязан покраснеть с названным именем спецификации. Возврат побайтовой копией со сверкой sha256, git checkout НЕ применялся, и после возврата харнесс отдельно печатает «post-restore live check: GREEN». MS1-MS7 снимают у контроля по одной способности отказать: полнота всегда пуста, UNCHECKED молча пропущен, reach утверждён вместо вычисления, нечитаемое тело зачтено читаемым, ветка STALE_ENTRY снята, шаблон стал вседозволенным, реестр испорчен. ЧЕСТНО: MS5 в первом прогоне SURVIVED — я нацелил его селектор на не тот тест; дефект был в ХАРНЕССЕ, не в покрытии, исправлен и убит вторым прогоном. | ПОЛНАЯ ЛЕНТА: 7547 passed, 24 skipped, 0 failed за 74.55 с (pytest из PATH, -p no:cacheprovider, память #450); было 7521, прирост ровно на 26 новых. mypy и ruff по новым файлам чисто. Квитанция: verification_run #1906, signed, key 103a83a212851018, scope=high; недекларированных файлов НЕТ (дерево было чистым на старте задачи). | ЧТО КОНТРОЛЬ НАШЁЛ И ЧТО ЭТО ЗНАЧИТ: renar-adoption помечен UNCHECKED поимённо — перечислимый предмет его тела никто не назвал, а content_ref указывает на decisions#109, то есть на ЗАПИСЬ, а не на читаемый файл. Зелёным он не зачтён: отсутствие отрицательной находки не есть положительный вердикт (SENAR 1.4 §8.6(e)). Это первая настоящая находка контроля, и живое состояние закреплено тестом test_the_live_repository_reports_exactly_the_gap_it_has, так что дать renar-adoption тело-файл нельзя молча — тест потребует обновления.
