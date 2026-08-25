---
slug: skill-bundle-from-vendor-repo
title: "3.5: бандлы недоступны из магазина — bundle резолвит skills-official/, которого в поднятом проекте нет"
status: done
epic: landscape-2026-h2
story: l26-ecosystem
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: "НЕ вписывать имена внутренних скиллов (deck, noslop и прочие из [вычеркнуто: internal-host]/kibertum/clients/kibertum/tausik/skills) в skills-official/bundles.json или любой другой файл ядра: skills-official/ есть исходник ПУБЛИЧНОГО github.com/Kibertum/tausik-skills, а ядро зеркалится в публичный github.com/Kibertum/tausik-core. Конвенция «Внутренний магазин скиллов не утекает в публичный github», ошибка необратима. НЕ трогать механизм клонирования репозиториев (clone_repo, доверие URL, --force) — предмет задачи это резолв состава бандла, а не добыча репозиториев. НЕ менять формат tausik-skills.json."
relevant_files:
  - "scripts/skill_bundles.py"
  - "scripts/project_cli_skill.py"
  - "tests/test_skill_bundles_from_repo.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/skill_bundles.py"
  - "scripts/project_cli_skill.py"
  - "scripts/skill_repos.py"
  - "skills-official/bundles.json"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-28T14:45:34Z"
---

## Goal

Подтверждено: scripts/project_cli_skill.py:158-162 ищет skills-official/ рядом с чекаутом ядра, а bundles.json не живёт в репозитории магазина. Из-за этого deck нельзя вписать в workflow-helpers, а noslop — в ru-locale; бандл ru-locale остаётся пустым placeholder'ом. Решить, откуда бандл берёт состав: из вендор-репы (bundles.json рядом с tausik-skills.json) или из ядра со ссылками на репозиторий:скилл. Первое даёт магазину владеть своими бандлами.

## Acceptance Criteria

AC1. Принято и зафиксировано через tausik decide решение об источнике состава бандла: вендор-репа (bundles.json рядом с tausik-skills.json) ИЛИ ядро со ссылками repo:skill. Первое даёт магазину владеть своими бандлами.
AC2. Резолв бандлов больше не требует наличия skills-official/ рядом с чекаутом ядра (project_cli_skill.py): бандл резолвится в поднятом проекте без вендор-каталога ядра — тест fails-then-passes.
AC3 [ПЕРЕСПЕЦИФИЦИРОВАН В СЕССИИ #150 — исходная формулировка требовала действия, ЗАПРЕЩЁННОГО конвенцией проекта]. Исходно требовалось: «бандлы deck (в workflow-helpers) и noslop (в ru-locale) резолвятся; бандл ru-locale больше не остаётся пустым placeholder'ом». Замер: deck и noslop не существуют ни в этом репозитории, ни в одном склонированном вендор-репе. Согласно памяти проекта «Внутренний магазин скиллов не утекает в публичный github.com/Kibertum/tausik-skills» они живут во ВНУТРЕННЕЙ репе [вычеркнуто: internal-host]/kibertum/clients/kibertum/tausik/skills, тогда как skills-official/bundles.json есть ИСХОДНИК публичного репозитория. Вписать эти имена сюда значит опубликовать факт существования внутренних наработок, и та же память отмечает, что ошибка необратима. Поэтому AC3 читается так: МЕХАНИЗМ, позволяющий внутренней репе наполнить бандл, объявленный публичной репой пустым, реализован и доказан тестом — БЕЗ упоминания внутренних имён в публичных файлах. Конкретное наполнение deck и noslop делается в bundles.json ВНУТРЕННЕЙ репы, вне этого репозитория. Проверка: tests/test_skill_bundles_from_repo.py::test_two_stores_union_into_one_bundle_without_naming_each_other, который среди прочего утверждает отсутствие приватного имени в публичном манифесте.
AC4. НЕГАТИВНЫЙ: отсутствующий или битый bundles.json даёт понятную ошибку, а не молча пустой бандл. Различаются два разных случая: ни одна репа не предоставляет бандлов (совет — добавить репу) и манифест конкретной репы битый (называется виновная репа).
AC5. Публичный манифест skills-official/bundles.json остаётся КОРРЕКТНЫМ БЕЗ ПРАВОК: публично ru-locale действительно пуст, и правило слияния снимает с него признак placeholder только тогда, когда его наполнит другая репа. Отсутствие диффа в этом файле есть требование, а не упущение.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert коммита задачи. Изменения затрагивают только резолв бандлов (scripts/skill_bundles.py, scripts/project_cli_skill.py) и манифест skills-official/bundles.json; схема БД, данные и установленные скиллы не трогаются. Откат возвращает прежний резолв «skills-official/ рядом с чекаутом ядра» — то есть прежнее поведение, при котором бандлы не резолвятся в поднятом проекте. Проверка отката: `tausik skill bundle list` отрабатывает в репозитории ядра (где skills-official/ существует). Уже установленные бандлом скиллы откат НЕ удаляет — установка идёт поштучно через существующий skill_install и от резолва бандла не зависит.

## Journal

- 2026-07-28T14:43:54Z [implementation] — AC3 ПЕРЕСПЕЦИФИЦИРОВАН, потому что исходная формулировка требовала действия, ЗАПРЕЩЁННОГО конвенцией проекта, и я это фиксирую явно, а не тихо обхожу. Замер: (1) каталогов deck и noslop нет ни в skills-official/, ни в .tausik/vendor/ (5 склонированных реп: anthropic-official, polyakov, seo, trailofbits, ui-ux-pro-max), ни где-либо в дереве; (2) единственная зарегистрированная репа формата tausik-skills — tausik-skills, помечена [not cloned], указывает на https://github.com/Kibertum/tausik-skills; (3) память проекта «Внутренний магазин скиллов не утекает в публичный github.com/Kibertum/tausik-skills» прямо говорит: внутренний репозиторий [вычеркнуто: internal-host]/kibertum/clients/kibertum/tausik/skills — «здесь живут наработки (noslop, deck и прочее). Остаётся внутри», и «ошибка тут необратима: опубликованное нельзя развидеть». Файл skills-official/bundles.json есть ИСХОДНИК публичного репозитория. Следовательно исходный AC3 («вписать deck в workflow-helpers, noslop в ru-locale») означал записать имена внутренних наработок в публикуемый файл. Это же соображение оказалось РЕШАЮЩИМ для AC1 и записано в решении #200: вариант «ядро со ссылками repo:skill» отвергнут не по вкусу, а потому что ядро зеркалится в публичный github.com/Kibertum/tausik-core, то есть тот вариант нарушал бы границу публикации ПО ПОСТРОЕНИЮ. Реализовано вместо этого правило слияния по имени бандла: два магазина, объявившие один бандл, ОБЪЕДИНЯЮТ списки скиллов. Публичная репа объявляет ru-locale пустым placeholder'ом, внутренняя добавляет в него noslop, и ни один файл не называет содержимое другого. Признак placeholder снимается автоматически, как только бандл кем-то наполнен. Проверено tests/test_skill_bundles_from_repo.py::test_two_stores_union_into_one_bundle_without_naming_each_other, который среди прочего читает публичный манифест и утверждает, что приватного имени в нём НЕТ. Добавлен AC5: отсутствие диффа в skills-official/bundles.json есть требование, а не упущение — публично ru-locale действительно пуст, и манифест остаётся правдивым без правок.
- 2026-07-28T14:45:24Z [implementation] — AC-1: ✓ решение #200 — состав бандла принадлежит репозиторию-магазину, bundles.json едет рядом с tausik-skills.json; вариант «ядро со ссылками repo:skill» отвергнут по границе публикации, а не по вкусу. AC-2: ✓ tests/test_skill_bundles_from_repo.py::test_bundle_resolves_from_a_cloned_repo_with_no_core_checkout — fails-then-passes в одном тесте: сначала утверждается, что СТАРЫЙ резолв (только каталог рядом с ядром) поднимает BundleError, затем что новый discover_manifest_dirs находит бандл в склонированной репе при полностью отсутствующем skills-official/. AC-3: ✓ tests/test_skill_bundles_from_repo.py::test_two_stores_union_into_one_bundle_without_naming_each_other — механизм наполнения бандла приватным магазином реализован и доказан, включая утверждение, что приватное имя ОТСУТСТВУЕТ в публичном манифесте. Переспецификация обоснована отдельной записью журнала. AC-4: ✓ tests/test_skill_bundles_from_repo.py::test_no_store_provides_bundles_says_so_instead_of_reporting_an_empty_bundle, ::test_corrupt_manifest_in_one_store_is_reported_not_swallowed, ::test_manifest_with_wrong_root_type_is_rejected — три негативных пути, два разных отказа разведены и виновная репа называется поимённо. AC-5: ✓ `git diff --stat skills-official/bundles.json` пуст — публичный манифест не тронут, как и требуется. AC-6/CHANGELOG: ✓ CHANGELOG.md и CHANGELOG.ru.md обновлены прозой на обоих языках; verification_run #1565 (green, exit=0); ruff clean, mypy Success 313 файлов, filesize exit 0, bootstrap --ide all прогнан, doctor «OK All clean», 500 тестов среза skill/bundle зелёные. Domain: результат осмыслен вне тестов — `.tausik/tausik skill bundle list` вживую печатает 6 бандлов (integrations 4, data-formats 3, quality-pro 5, automation 3, workflow-helpers 5, ru-locale 0 placeholder), то есть в репозитории ядра поведение не изменилось, а в поднятом проекте, где раньше команда падала, теперь читаются бандлы склонированных магазинов. Обратная совместимость сохранена: тест test_single_directory_argument_still_works пришпиливает вызов с ОДНИМ каталогом, которым пользуются существующие тесты и сам фреймворк.
