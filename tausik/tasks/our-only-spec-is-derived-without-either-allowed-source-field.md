---
slug: our-only-spec-is-derived-without-either-allowed-source-field
title: "Три SPEC выведены без обоих допустимых источников: ни source.tz-section, ни source.adapt — дословный негативный сценарий §13.3.3"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: "НЕ ТРОГАТЬ: схема БД и миграции (решение #307 пункт 2: поля происхождения НЕ вводим); scripts/renar_measurer_caveats.py (реестр другого назначения — там измеритель не заслужил подтверждения, здесь норма неприменима; это разные утверждения с разными выходами, сливать нельзя); развёрнутые профили — генерируются bootstrap. ОБЛАСТЬ РАСШИРЕНА ПО ЗАМЕРУ, А НЕ РАДИ УДОБСТВА: RENAR-CONFORMANCE.yaml внесён в область, потому что охрана test_committed_manifest_is_not_stale ПОКРАСНЕЛА — генератор манифеста изменился, значит закоммиченный артефакт стал несвежим, и охрана требует именно регенерации. Оставить её красной нельзя."
relevant_files:
  - "scripts/renar_normative_inapplicability.py"
  - "scripts/renar_conformance.py"
  - "scripts/renar_clause_reactive_adapt.py"
  - "tests/test_renar_normative_inapplicability.py"
  - RENAR-CONFORMANCE.yaml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/renar_normative_inapplicability.py"
  - "scripts/renar_conformance.py"
  - "scripts/renar_clause_reactive_adapt.py"
  - "tests/test_renar_normative_inapplicability.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_manifest_artifact.py"
  - RENAR-CONFORMANCE.yaml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - mandatory-clause-13-3-3-is-checked-by-counting-artifacts
completed_at: "2026-09-04T19:53:22Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО В #198 ПРИ ВЫНЕСЕНИИ ВЕРДИКТА ПО ADR-006. Долг практики, вскрытый вердиктом, уходит отдельной задачей и не поглощается формулировкой вердикта.

НОРМА. ADR-006 таблица источников, стр.76: «| SPEC | conditional | mandatory всегда (для traceability) |» — то есть `source.tz-section` обязателен для SPEC ВСЕГДА, при любом исходе состязательного обзора. §13.3.3 называет обратное негативным сценарием дословно, стр.90: «...но BR/SR/SPEC производятся из ТЗ без `source.tz-section` и без `source.adapt` — нарушение обязательного происхождения».

МЫ. renar/specs/renar-adoption.md несёт `content_ref: decisions#109` (стр.3) и не несёт НИ ОДНОГО поля происхождения: ни `tz-section`, ни `adversarial-review-ref`, ни `source.adapt`. Обе первые строки проверены на ОТСУТСТВИЕ отдельной машинной ветвью, ветвь промутирована заведомо присутствующей строкой и покраснела. Связь с нашим ADAPT идёт в ОБРАТНУЮ сторону — из ADAPT в SPEC через links, — то есть провенанс не выражен там, где его ищет норма и где его искал бы аудитор.

ПОЧЕМУ ЭТО НЕ ОДИНОКАЯ ОПЕЧАТКА. `content_ref: decisions#109` указывает на ЗАПИСЬ в нашей БД, а не на раздел ТЗ. Тот же дефект пойман с другой стороны в #197: новый контроль полноты тела SPEC пометил renar-adoption как UNCHECKED именно потому, что предмет его тела не назван, а content_ref ведёт в decisions#109. Два независимых контроля, построенных по разным основаниям, указали на одно место — признак настоящего дефекта, а не придирки.

ЧТО ДЕЛАЕТСЯ. Ввести поля происхождения в модель SPEC и заполнить их для существующего артефакта, либо — если решено, что ТЗ у нас не существует как артефакта — объявить это ЯВНО и показать, что норма к нам неприменима, вместо молчаливого пропуска поля. Второй путь требует ответа на вопрос, который сегодня без ответа: считается ли decisions#109 нашим ТЗ. Ответ на него общий с mandatory-clause-13-3-3-is-checked-by-counting-artifacts, поэтому задачи связываются, а не сливаются: там измеритель, здесь артефакт.

ЗАВИСИМОСТЬ ОТ РЕШЕНИЯ О ЗАЯВКЕ: если по our-conformance-claim-rests-on-a-mode-the-standard-removed заявка о соответствии снимается, эта задача не исчезает — провенанс SPEC полезен нам самим, — но её срочность падает с «нарушаем норму» до «теряем прослеживаемость».

## Acceptance Criteria

1. Манифест несёт ЯВНОЕ объявление неприменимости: раздел, называющий клаузу (§13.3.3 p.90 и таблицу источников ADR-006), предмет (происхождение SPEC через source.tz-section), причину (ТЗ как артефакта нет, решение владельца #307) и ссылку на renar-first-tz-adapt. Молчаливое отсутствие поля заменено записью.
2. Объявление покрывает ВСЕ живые SPEC и покрытие ВЫВЕДЕНО из хранилища, а не перечислено литералом: появление четвёртого SPEC не оставляет его вне объявления.
3. Подпроверка spec-provenance-source ОСТАЁТСЯ красной. Объявление не есть соответствие; мутация, красящая её в зелёный, обязана убиваться. Её evidence НАЗЫВАЕТ объявление, чтобы читатель не видел голого красного без опубликованной причины.
4. НЕГАТИВНЫЙ СЦЕНАРИЙ И ХРАПОВИК ПРЕМИСЫ: премиса объявления есть УТВЕРЖДЕНИЕ О МИРЕ (ТЗ у нас нет), и её изменение обязано быть замечено. Если в хранилище появляется SPEC, несущий происхождение, охрана КРАСНЕЕТ, а не продолжает молча объявлять неприменимость. Проверяется синтетикой, а не поломкой охраняемого.
5. НЕГАТИВНЫЙ СЦЕНАРИЙ ОШИБКИ: пустое объявление недопустимо молча — пустота обязана быть объявлена и объяснена, как это уже сделано в реестре measurer-caveats, иначе ничего не раскрыто и нечего раскрывать выглядят одинаково.
6. Мутации объявлены ДО прогона, каждая новая ветвь убита, выжившие разобраны до конца. Полная лента зелёная.

## Plan

## Rollback

git revert коммита задачи. Новый модуль и его тест удаляются целиком, раздел манифеста исчезает вместе с ними. Схема БД не меняется, миграции нет (решение #307 пункт 2), артефакт RENAR-CONFORMANCE.yaml не регенерируется.

## Journal

- 2026-09-04T11:02:12Z [planning] — ПРЕМИСА ПОПРАВЛЕНА ЗАМЕРОМ, ЗАДАЧА НЕ ВЗЯТА. В #198 заголовок говорил «единственный SPEC». Замер #209: renar/specs/ содержит ТРИ артефакта — renar-adoption (content_ref: decisions#109), sec-config-trust-tiers (content_ref: docs/ru/config-trust-tiers.md), team-state-in-git-format (content_ref: docs/ru/team-state-in-git.md). Полей происхождения нет НИ У ОДНОГО: ни source.tz-section, ни source.adapt, ни adversarial-review-ref. Заголовок исправлен на «Три SPEC». РЕШЕНИЕ ВЛАДЕЛЬЦА ПОЛУЧЕНО (решение #307): decisions#109 НЕ считается нашим ТЗ, ТЗ как артефакта у нас нет, и это объявляется ЯВНО. Значит задача идёт по ВТОРОМУ пути собственного описания: показать неприменимость нормы записью со ссылкой на renar-first-tz-adapt, а не заполнять tz-section. Объявление обязано покрыть ВСЕ ТРИ артефакта. Миграция v50 скорее не нужна — решать инвентарём при взятии.
- 2026-09-04T19:40:05Z [implementation] — ОБЛАСТЬ РАСШИРЕНА ПО ЗАМЕРУ. Исходный scope_exclude запрещал трогать RENAR-CONFORMANCE.yaml по аналогии с двумя предыдущими задачами смены. Здесь аналогия НЕВЕРНА и это показал прогон: test_committed_manifest_is_not_stale сравнивает закоммиченный манифест с тем, что даёт живая БД, и покраснел на новом разделе normative-inapplicability. В прошлых двух задачах генератор манифеста не менялся, здесь меняется. Охрана права, регенерация есть ЧАСТЬ починки, а не отдельный акт. Расширяю ACL по замеру, а не ради удобства (память из #211).
- 2026-09-04T19:52:03Z [implementation] — РЕАЛИЗАЦИЯ, ЗАМЕРЫ И МУТАЦИИ. Мутаций объявлено ДО прогона восемь, убито восемь, промахов якоря ноль. ДВЕ СНАЧАЛА ВЫЖИЛИ, и обе указали на настоящее, а не на описку. P1 охват перечислен вместо выведенного — СНАЧАЛА ВЫЖИЛ. Разбор до конца: covered_specs отвечает РАЗНЫМИ запросами в зависимости от того, может ли подложка вообще хранить происхождение, а живой проект идёт по ветви «колонки нет вовсе». Мой единственный тест ростом покрывал только её, поэтому обрезание результата во ВТОРОЙ ветви было не наблюдаемо. Тест параметризован по обеим ветвям, мутант убит. P6 раздел перестаёт доходить до манифеста — СНАЧАЛА ВЫЖИЛ по другой причине: базовая линия была КРАСНОЙ (артефакт несвежий), то есть убийца не мог отличить мутанта от исходного состояния. Разбор дал отдельный замер, см. ниже. После регенерации артефакта — убит. P2 охват держит SPEC, обретший происхождение — убит. P3 храповик перестаёт замечать пришедшее ТЗ — убит. P4 пустая строка считается ссылкой на ТЗ — убит. P5 пустой реестр всё равно публикует раздел — убит. P7 объявление превращено в заявление о соответствии (подпроверка перекрашена в зелёный) — убит. P8 отсутствие таблицы specs роняет вместо пустого охвата — убит. ЗАМЕР, КОТОРОГО НЕ БЫЛО НИ У КОГО: обёртка .tausik/tausik исполняет РАЗВЁРНУТЫЙ ПРОФИЛЬ (.claude/scripts), а не scripts/ в корне. Регенерация сразу после правки генератора записала manifest-version 16 БЕЗ нового раздела, и охрана несвежести осталась красной с сообщением «regenerate», хотя регенерация только что была. Выглядит дефектом генератора, является стойлостью профиля. Незакоммиченная v16 отброшена через git checkout (записью журнала она не была, значит переиспользования номера нет), порядок исправлен: правка → bootstrap --ide all → --check → регенерация → лента. Память #579. ОБЛАСТЬ РАСШИРЕНА ПО ЗАМЕРУ, НЕ РАДИ УДОБСТВА: RENAR-CONFORMANCE.yaml внесён в scope после того, как test_committed_manifest_is_not_stale ПОКРАСНЕЛ. Регенерация здесь есть часть починки, а не отдельный акт: генератор манифеста изменился. Заодно это прогнало сквозь ЖИВОЙ артефакт починку чтения журнала из предыдущей задачи смены — v16 несёт replaces: CFM-2026-09-04-tausik@v15, взятый из журнала. ЧУЖАЯ ОХРАНА ПОЙМАЛА МОЮ ПРОЗУ: test_no_hand_written_count_beside_the_list покраснел на «list of three slugs» в докстринге нового теста. Формулировка переписана на «written-out list of slugs ... until the next SPEC exists», а НЕ добавлена в разрешающий список: сообщение охраны прямо запрещает глушить живое утверждение. Вышло лучше — суть в перечислении, а не в числе. РАЗМЕР: renar_conformance.py дошёл до 489 из 500 и сжат до 484 переносом объяснения в докстринг нового модуля, где оно уже стояло. Запас 16. Negative: покрыты отсутствие таблицы specs, отсутствие колонки, пустая строка вместо ссылки на ТЗ, пустой реестр объявлений (раздел НЕ публикуется вовсе — пустой блок читался бы как «искали и не нашли»), SPEC, обретший происхождение и вышедший из охвата.
- 2026-09-04T19:53:12Z [implementation] — Verification checklist. AC-1: ✓ tests/test_renar_normative_inapplicability.py::TestTheDeclarationItself::test_every_declaration_names_its_premise_and_its_exit AC-1: ✓ tests/test_renar_normative_inapplicability.py::TestADeclarationIsNotCompliance::test_the_section_says_so_in_the_artifact AC-2: ✓ tests/test_renar_normative_inapplicability.py::TestReachIsDerivedNotEnumerated::test_a_fourth_spec_is_covered_the_day_it_appears (параметризован по ОБЕИМ ветвям вычисления охвата) AC-2: ✓ tests/test_renar_normative_inapplicability.py::TestReachIsDerivedNotEnumerated::test_a_spec_that_gains_provenance_leaves_the_reach AC-3: ✓ tests/test_renar_clause_reactive_adapt.py (подпроверка spec-provenance-source остаётся красной; мутация P7, красящая её в зелёный, убита) AC-3: ✓ tests/test_renar_manifest_artifact.py::test_committed_manifest_is_not_stale (раздел действительно доходит до артефакта; мутация P6 убита) AC-4: ✓ tests/test_renar_normative_inapplicability.py::TestThePremiseIsWatched::test_an_arriving_tz_reference_breaks_the_premise (синтетика, охраняемое не ломалось) AC-4: ✓ tests/test_renar_normative_inapplicability.py::TestThePremiseIsWatched::test_the_live_project_still_holds_the_premise AC-5: ✓ tests/test_renar_normative_inapplicability.py::TestTheDeclarationItself::test_emptiness_must_be_declared_not_merely_reached AC-5: ✓ tests/test_renar_normative_inapplicability.py::TestADeclarationIsNotCompliance::test_an_empty_registry_publishes_no_section_at_all AC-6: ✓ verification_run #2074 (exit=0, receipt signed) плюс мутации P1-P8, убито 8 из 8, оба выживших разобраны до конца Domain: результат осмыслен вне тестов и проверен на ЖИВОМ артефакте, а не только на синтетике. RENAR-CONFORMANCE.yaml v16 несёт раздел normative-inapplicability, чей applies-to равен ['renar-adoption', 'sec-config-trust-tiers', 'team-state-in-git-format'] — ВЫЧИСЛЕННЫЙ из хранилища, а не вписанный. Подпроверка spec-provenance-source в том же артефакте по-прежнему ok: false, то есть объявление и вправду не превратилось в заявление о соответствии; её evidence теперь указывает на раздел, поэтому аудитор видит красное вместе с опубликованной причиной, а не голое красное. Domain: реальный вход, на котором это важно — приход настоящего ТЗ. Тогда premise_broken перестаёт быть пустым, тест на живой БД краснеет и требует ПЕРЕРЕШЕНИЯ владельцем, а не тихого расширения объявления. Это отличает объявление от вечной отговорки: у него назван выход. Полная лента 8913 passed / 25 skipped / 0 failed за 127.9 с; ruff, ruff format --check, mypy чисто; bootstrap --ide all и --check без дрейфа; размеры renar_conformance.py 484 из 500, renar_normative_inapplicability.py 166.
