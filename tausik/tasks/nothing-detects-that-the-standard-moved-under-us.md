---
slug: nothing-detects-that-the-standard-moved-under-us
title: "Никто не замечает, что стандарт ушёл вперёд: отставание нашли разбором вручную, а не проверкой"
status: done
epic: release-19-renar-conformance
story: standards-drift-detection
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "scripts/renar_standard_drift.py (новый), scripts/renar_drift.py (регистрация в _DETECTORS), scripts/project_parser.py или project_parser_* (choices детектора), scripts/project_cli_*.py (передача), tests/test_renar_standard_drift.py (новый), CHANGELOG.md, CHANGELOG.ru.md, .tausik/config.json (ключ пути, машинно-локальный)"
scope_exclude: "standards/renar (корпус только читается, НИКОГДА не изменяется); сетевая сверка с renar.tech; реализация самих отозванных норм (ADR-011 — своя задача adapt-dual-signature-implements-a-withdrawn-norm)"
relevant_files:
  - "scripts/renar_standard_drift.py"
  - "scripts/project_cli_drift.py"
  - "scripts/project_parser.py"
  - "tests/test_renar_standard_drift.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-06T12:19:09Z"
---

## Goal

Причина всего эпика: об отставании от RENAR ADR-011 и ADR-013 мы узнали разбором в сессии #178, а не проверкой. Между отзывом нормы и обнаружением прошли месяцы, и всё это время справка CLI объявляла отозванную редакцию пользователям. RENAR сейчас идёт по ветке v1-1-wave с шестью предложенными ADR, поэтому следующий сдвиг не гипотеза, а расписание. У нас уже генерируется RENAR-CONFORMANCE.yaml, но он сверяет живую БД с НАШИМ представлением о стандарте — то есть не поймал бы ни одного из двух найденных расхождений. Задача: сверять с САМИМ стандартом. Проверяемые величины называются заранее и по существу: состав закрытых списков (типы SPEC, типы TC, категории обратных находок), требования к подписям по артефактам, номер версии корпуса. Источник — локальный репозиторий standards/renar по решению владельца (#255). НЕГАТИВНОЕ ограничение: детектор обязан отличать ПРИНЯТОЕ от ПРЕДЛОЖЕННОГО и не требовать реализации proposed ADR — иначе он будет краснеть постоянно и его отключат. Отдельным пунктом: расхождение локального корпуса с опубликованным на renar.tech — тоже находка, но ДРУГАЯ, и подаётся отдельно.

## Acceptance Criteria

AC-1 (сверка с САМИМ корпусом, не с нашим представлением): новый детектор читает канонический текст стандарта (standards/renar/standard/*.md) и сверяет с нашими объявлениями: закрытый список типов SPEC (§8.3), категории обратных находок (§7.4.4), статусы ADAPT (§7.8.1), номер версии корпуса против RENAR_VERSION. Значения берутся ИЗ ТЕКСТА разбором, а не переписываются в код.
AC-2 (три состояния, как у остальных читателей): корпус отсутствует (путь не задан или каталога нет) — «не проверено», отдельный исход, НЕ «дрейфа нет»; корпус есть, но глава не разбирается — находка «нечитаемо»; корпус разобран — вердикт по существу. Тесты на все три.
AC-3 (принятое против предложенного, негативное ограничение задачи): детектор читает status во фронтматтере ADR. Находкой считается ТОЛЬКО ADR со статусом, начинающимся на accepted, чей идентификатор не упоминается нигде в нашем репозитории. ADR со статусом proposed/draft/superseded НЕ является находкой ни при каких условиях — тест подкладывает предложенный ADR и требует тишины.
AC-4 (красная ветвь выразима): синтетический корпус, где §8.3 называет двенадцатый тип, где §7.4.4 теряет категорию, где версия корпуса выше нашей, где лежит принятый ADR, о котором наш репозиторий молчит, — каждая даёт находку с указанием главы и того, что именно разошлось. Зелёная ветвь: живой корпус сегодня даёт ноль находок (или ровно те, что записаны в журнал как известные и объяснённые).
AC-5 (детектор не блокирует и не требует сети): warn-only, read-only, корпус не изменяется; расхождение локального корпуса с опубликованным на renar.tech в этой задаче НЕ строится — объявлено в докстринге как ДРУГАЯ находка с указанием, что для неё нужно (сеть в гейте) и почему её здесь нет.
AC-6: детектор доступен как `tausik drift --detector standard` и в run_all не ломает существующие детекторы (они принимают соединение, этот — путь); renar_drift.py не растёт (новый модуль); полный прогон, mypy, ruff; мутации объявлены и убиты по ветви либо объявлены эквивалентными; CHANGELOG в обоих файлах; путь к корпусу берётся из конфига с объявленным дефолтом и НЕ хардкодится в модуле.

## Plan

## Rollback

Новая проверка дрейфа стандарта, read-only. Откат: git revert либо отключение в конфиге гейтов. Локальный корпус standards/renar не изменяется ни при каких условиях.

## Journal

- 2026-09-06T12:06:03Z [implementation] — ПОЧИНКА. Новый scripts/renar_standard_drift.py (393 строки, вне renar_drift, который уже 458): corpus_root читает путь из конфига (ключ renar_standard_corpus, дефолт — отсутствие, НЕ хардкод); closed_list_from разбирает ДВЕ формы, в которых корпус пишет перечни — бэктики в прозе (§8.3, §7.4.4) и pipe-форму фронтматтера (§7.8.1); corpus_version читает баннер «Часть RENAR Standard vX.Y»; accepted_adrs читает status из фронтматтера ADR; adrs_mentioned_in спрашивает git grep ОДНИМ вызовом по отслеживаемым файлам (4000 файлов читать не нужно) и отличает «не нашли» от «не смогли спросить». detect_standard_drift даёт находки трёх классов: version-behind, <list>-drift, accepted-adr-unreckoned, плюс corpus-unreadable и repo-unreadable. corpus_status печатает, ПРОВЕРЕН ли корпус вообще — отдельной строкой, потому что «дрейфа нет» и «корпуса нет» иначе выглядят одинаково, а именно это и стоило нам месяцев. CLI: tausik drift --detector standard (и в all), выбор расширен, supersession заодно добавлен в choices — он был в реестре, но не в справке. ЗАМЕР НА ЖИВОМ КОРПУСЕ: version 1.0 совпадает, три перечня совпадают, из тринадцати принятых ADR ни один не остался неупомянутым — ноль находок; ADR-011 (accepted-pending-adr-012) распознаётся как принятый. ГРАБЛИ, ПОЙМАННЫЕ ПРОГОНОМ: (1) формулировки cue я СНАЧАЛА ПРИДУМАЛ, и две из трёх не совпали с корпусом — исправлено чтением текста; (2) pipe-форма не разбиралась одной регуляркой из-за пробелов вокруг черты — заменено split-ом с требованием, что ВСЕ части суть имена, иначе строка нечитаема целиком; (3) тест «корпуса нет» на этой машине измерял ЖИВОЙ корпус, потому что root=None значит «спроси конфиг» — отсутствие теперь моделируется monkeypatch-ем. МУТАЦИИ 12 объявлено, 12 убито, но ДВЕ сначала выжили ПО МОЕЙ ВИНЕ: S5 был написан как no-op ([] or [x] равно [x]) — переписан на настоящее удаление находки и убит; S9 (снятие нормализации префикса SPEC-) не убивался, потому что МОЯ СИНТЕТИКА не воспроизводила форму корпуса (в §8.3 префикс несёт только первый член) — фикстура исправлена, S9 убит. Второй случай — настоящая находка о качестве фикстуры, а не о мутации.
- 2026-09-06T12:19:06Z [implementation] — AC-1: ✓ scripts/renar_standard_drift.py читает канонический текст корпуса и сверяет типы SPEC (§8.3), категории находок (§7.4.4), статусы ADAPT (§7.8.1) и редакцию; значения разбираются из текста — tests/test_renar_standard_drift.py::test_the_lists_are_parsed_in_the_shapes_the_corpus_writes_them, tests/test_renar_standard_drift.py::test_an_agreeing_corpus_is_silent (мутации S1, S2, S3, S9 убиты) AC-2: ✓ три состояния — tests/test_renar_standard_drift.py::test_no_corpus_is_not_checked_and_says_so («не проверено», отдельная строка corpus_status), tests/test_renar_standard_drift.py::test_a_configured_path_that_is_not_there_is_no_corpus (мутация S12 убита), tests/test_renar_standard_drift.py::test_a_chapter_that_will_not_parse_is_a_finding_not_a_silence и tests/test_renar_standard_drift.py::test_a_missing_chapter_is_a_finding (мутация S5 убита), tests/test_renar_standard_drift.py::test_a_corpus_without_a_version_banner_is_a_finding (мутация S4 убита) AC-3: ✓ tests/test_renar_standard_drift.py::test_an_accepted_adr_nobody_mentions_is_a_finding, tests/test_renar_standard_drift.py::test_an_accepted_adr_we_have_read_is_silent, tests/test_renar_standard_drift.py::test_accepted_pending_still_counts (ADR-011). Negative: tests/test_renar_standard_drift.py::test_a_proposed_adr_is_never_a_finding параметризован по proposed/draft/superseded/rejected — предложенное НИКОГДА не находка (мутации S6, S7 убиты); tests/test_renar_standard_drift.py::test_not_being_able_to_ask_the_repo_is_stated_not_assumed — «не смогли спросить» отличается от «нечего искать» (мутация S8 убита) AC-4: ✓ красные ветви на синтетическом корпусе — tests/test_renar_standard_drift.py::test_a_twelfth_spec_type_is_a_finding, ::test_a_category_the_standard_dropped_is_a_finding, ::test_a_status_the_standard_renamed_is_a_finding, ::test_a_newer_edition_is_a_finding; каждая находка называет главу и что именно разошлось. Зелёная ветвь на живом корпусе: tests/test_renar_standard_drift.py::test_the_live_corpus_agrees_with_us (ноль находок; пропуск там, где корпуса нет) AC-5: ✓ warn-only и read-only: severity=warn у каждой находки, корпус только читается, гейтом детектор НЕ подключён (корпус есть не на каждой машине — записано в docs/{ru,en}/cli.md); сверка с renar.tech объявлена в докстринге модуля как ДРУГАЯ находка с указанием, что для неё нужна сеть в гейте и почему её здесь нет AC-6: ✓ `tausik drift --detector standard` и в составе `all` (проверено вызовом CLI после bootstrap); renar_drift.py не вырос — детектор в отдельном модуле, потому что принимает путь, а не соединение; docs/ru/cli.md и docs/en/cli.md описывают детектор и ключ конфига; путь берётся из renar_standard_corpus, дефолт — отсутствие Negative (форма разбора): tests/test_renar_standard_drift.py::test_a_partly_written_status_line_is_unreadable_not_a_shorter_list — строка с частью, не являющейся именем, нечитаема ЦЕЛИКОМ, а не даёт укороченный список (мутации S10, S11 убиты) Domain: RENAR §4.11 (классы дрейфа), §8.3/§7.4.4/§7.8.1 (закрытые списки корпуса), §13.4.3 (редакция как триггер переоценки), ADR-021 (контроль, умеющий покраснеть).
