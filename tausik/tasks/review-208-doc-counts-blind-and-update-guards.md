---
slug: review-208-doc-counts-blind-and-update-guards
title: "Ревью #208: три файла с числом 124 невидимы охраннику дрейфа, пустой title обнуляет stale, форма AR держится на одной колонке"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: epic-and-story-descriptions-cannot-be-updated
scope: null
scope_exclude: "N+1 в list_with_staleness не переписывается (замер 10.6 мс приемлем); спай таблицы мутаций не трогается; схема БД не меняется"
relevant_files:
  - "scripts/doc_drift_common.py"
  - "scripts/doc_drift_fixes.py"
  - "scripts/project_cli_renar.py"
  - "scripts/hierarchy_edit.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser_hierarchy.py"
  - "scripts/renar_clause_reactive_adapt.py"
  - "scripts/hooks/pwsh_write_parse.py"
  - "tests/test_hierarchy_update.py"
  - "tests/test_gen_doc_constants.py"
  - "tests/test_renar_clause_reactive_adapt.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_export.py"
  - "tests/test_renar_manifest_chain.py"
  - RENAR-CONFORMANCE.yaml
  - "docs/ru/architecture.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - README.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/doc_drift_common.py"
  - "scripts/doc_drift_fixes.py"
  - "scripts/renar_conformance.py"
  - "scripts/project_cli_renar.py"
  - "scripts/hierarchy_edit.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser_hierarchy.py"
  - "scripts/renar_clause_reactive_adapt.py"
  - "scripts/hooks/pwsh_write_parse.py"
  - "tests/test_hierarchy_update.py"
  - "tests/test_gen_doc_constants.py"
  - "tests/test_renar_clause_reactive_adapt.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_export.py"
  - "tests/test_renar_manifest_chain.py"
  - RENAR-CONFORMANCE.yaml
  - "docs/ru/architecture.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - README.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - AGENTS.md
scope_tools: []
depends_on: []
completed_at: "2026-09-04T09:21:28Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАВЕДЕНО ПЛАНОВЫМ РЕВЬЮ L3 #208 (записи БД #19–#23, opus, 8 проб) по коммитам 72c3b2c..0a316f3; долг по качеству работы той же смены. MEDIUM x3 (AC4 задачи об update не выполнен): docs/ru/architecture.md:110 «**117 project + 7 brain = 124 инструмента**» — файл в scope_paths и в CROSS_FILE_SCAN_TARGETS, но gen_doc_constants --check даёт OK: парный шаблон требует «(» перед числом, а шаблон жирного — чтобы число было жирным токеном; docs/{en,ru}/senar-compliance-matrix.md:82 — заголовок строки 124 противоречит своей же скобке (121 + 7); README.md:154-158 — пять ячеек таблицы IDE с 124, тогда как README.ru.md уже 128. MEDIUM (AR): разрез формы (tz_ref, verdict, status) отличает AR от ADAPT одной колонкой — adapts уже несёт две из трёх; миграция, добавившая adapts verdict и issued, опубликует «AR issued in adapts» — незаработанное усиление (#295); теста «класс с полной формой, но не AR, не считается» нет. LOW (берём): пустые --title/--description принимаются и пишут событие — единственный путь «пройти» отчёт, уничтожив замысел; граница created_at > vs >= не закреплена (мутация выжила); --stale-over 0 явно = «без фильтра» вопреки help; импорт hierarchy_edit посреди файла с noqa; entity_type во множественном числе против единственного у всех прочих событий (task, session, role…) — не задокументировано; докстринг pwsh переобещает, что pwsh резолвит .\x для НАТИВНЫХ команд (он передаёт токен как есть; починка — переобнаружение, верное направление); остаток «токен с кавычкой» должен быть в enforcement-coverage.md. LOW (не берём, названы): N+1 в list_with_staleness (10.6 мс на 107 эпиков — приемлемо); containment по абсолютным argv в спае (fail-red); журнальное «63 таблицы» не воспроизводится (71) — урок в память.

## Acceptance Criteria

AC1 ЧИСЛА И ИХ ОХРАННИК: docs/ru/architecture.md:110, docs/{en,ru}/senar-compliance-matrix.md:82 и README.md:154-158 несут 128 / 121; парный шаблон в doc_drift_common принимает форму без «(» и русскую форму «N инструмент(а|ов)», так что gen_doc_constants --check КРАСНЕЕТ на прежних строках (мутация: вернуть 124 в любой из трёх — --check exit 1, тест на каждую форму).
AC2 НЕГАТИВНЫЙ СЦЕНАРИЙ ОТЧЁТА: hierarchy_edit.update отказывает на пустых после strip --title/--description с ошибкой того же вида, что «nothing to update»; граница created_at закреплена тестом на задаче, созданной ровно в секунду правки (мутация > vs >= краснит); явный --stale-over 0 ведёт себя по help (help переписан: N=0 печатает все строки с числом); импорт hierarchy_edit в верхнем блоке без noqa; выбор entity_type (множественное число, совпадающее с kind проекции) записан в докстринге рядом с EDIT_EVENT.
AC3 ФОРМА AR ДЕРЖИТСЯ НЕ НА ОДНОЙ КОЛОНКЕ: семейство adapts исключается явно с цитатой (§7.4.1: AR — единственный носитель вердикта, ADAPT порождается ИЗ AR, значит ADAPT не есть свой состязательный обзор); тест «adapts с колонками verdict+status issued НЕ засчитывается как AR, evidence называет исключение» — красный на HEAD, зелёный после; мутации: исключение снято — тест краснеет.
AC4 pwsh: докстринг _paths_for_host говорит измеренное (переобнаружение, а не резолвинг pwsh для нативных команд); остаток «токен с кавычкой» записан в docs/{en,ru}/enforcement-coverage.md рядом с остатком computed-path. CHANGELOG.md и CHANGELOG.ru.md синхронно; ревью на починку L3 (память #536); bootstrap --ide all перед done; память ДО done.

## Plan

## Rollback

git revert коммита: числа в трёх документах возвращаются к 124, охранник дрейфа — к прежним шаблонам, update снова принимает пустые строки; гейты и данные не меняются

## Journal

- 2026-09-04T08:59:34Z [implementation] — ПОЧИНКА ПО ПЯТИ ЗАПИСЯМ РЕВЬЮ (#19–#23). Документы: docs/ru/architecture.md 117+7=124 -> 121+7=128; senar-compliance-matrix en/ru заголовок 124 -> 128; README.md пять ячеек 124 -> 128. Охранник doc_drift_common: пара без «(», «= N tools/инструментов», «MCP coverage N» — три новых шаблона + 5 тестов (4 формы красные, все формы зелёные при верном числе). hierarchy_edit: пустые title/description после strip — отказ «empty <field>» без события (тест на оба поля); граница created_at строго > закреплена тестом на задаче с created_at = времени события; entity_type во множественном числе задокументирован рядом с EDIT_EVENT; докстринг staleness называет границу. CLI: импорт hierarchy_edit в верхнем блоке без noqa; --stale-over default None, явный 0 — фильтр (тест _stale_rows на None/0/2), help переписан. AR: AR_SHAPE_FIELDS = (tz_ref, verdict, produces_adapt, status) — четвёртое обязательное поле §7.4.6, которое ADAPT нести не может (§7.4.1: ADAPT порождается ИЗ AR); фикстуры в трёх файлах получили колонку; новый тест: adapts с verdict + таблица adapts_v2 (tz_ref, verdict, status issued) НЕ засчитаны, evidence называет «lacks produces_adapt». pwsh: докстринг _paths_for_host говорит измеренное (переобнаружение, pwsh передаёт аргумент нативной команды как есть); остаток «токен с кавычкой» — в docs/{en,ru}/enforcement-coverage.md. МУТАЦИИ 8/8 (базовый --check rc=0, убито только rc=1): возврат 124 в каждый из трёх документов -> --check красный; страж пустых строк снят; > -> >=; явный 0 как «без фильтра»; produces_adapt снят из формы; пара снова требует «(». Память #547 до done.
- 2026-09-04T09:15:01Z [implementation] — ВТОРОЙ КРУГ ПО РЕВЬЮ НА ПОЧИНКУ (#24, 0/2/4/3). HIGH-1 цепь манифеста: replaces собирался как CFM-<сегодня>@v<n-1> (renar_conformance.py:379) — семь регенераций были в один день, первая через день (#208) дала ссылку на несуществующий CFM-2026-09-04@v13. Починка в project_cli_renar (renar_conformance.py на пределе 499 строк): _existing_manifest -> (version, id), previous_link(path) = '<id>@v<version>' предшественника, cmd_renar подставляет его в replaces и перерисовывает yaml; тест tests/test_renar_manifest_chain.py: unit на previous_link (вчерашний предшественник — сегодня тот же), нет файла/нет id -> None, и ЖИВОЙ тест: replaces текущего манифеста обязан называть (version, id), который держит git по истории файла. Регенерация выполнена ОТ ЗАКОММИЧЕННОГО v13 (промежуточный незакоммиченный v14 снят git checkout): v14 replaces CFM-2026-09-03-tausik@v13. HIGH-2: docs/{en,ru}/mcp.md:11 117 -> 121 + шаблон «project-scoped tools/инструменты (N)» (RU-множественное потребовало инструмент\w*). MEDIUM: fixer теперь ходит и по MCP_COUNT_EXTRA_TARGETS; CHANGELOG ru/en про AR синхронизированы и «замерено тогда же»; комментарий формы AR объясняет, почему reviewer/primary/signature (вложенные записи) вне разреза, тест переименован в scalar_mandatory_fields; README-проза «the same N tools» под охраной, ячейки таблицы — НЕТ (решение владельца: убрать счёт по строкам). LOW: страж пустых строк после _require; «= N tools» заякорен на brain =. МУТАЦИИ ещё 3/3: ссылка снова из даты -> красный; шаблон project-scoped снят -> красный; страж до _require -> красный (unknown_slug). Полный набор затронутых файлов: 193 passed.
- 2026-09-04T09:20:34Z [implementation] — AC-1: ✓ tests/test_gen_doc_constants.py::test_scan_mcp_counts_sees_the_forms_review_208_found_blind (7 форм) и tests/test_gen_doc_constants.py::test_scan_mcp_counts_accepts_the_same_forms_when_right; три возврата 124 в документы -> --check exit 1 (журнал); docs/mcp.md 117 -> 121 с шаблоном. AC-2: ✓ tests/test_hierarchy_update.py::TestUpdate::test_an_empty_string_is_refused_and_writes_nothing, tests/test_hierarchy_update.py::TestStaleness::test_a_task_created_in_the_same_second_as_the_edit_is_not_counted, tests/test_hierarchy_update.py::TestCallers::test_stale_over_zero_is_a_filter_and_no_flag_is_none; импорт в верхнем блоке; entity_type задокументирован. Negative: пустые строки — отказ без события; мутации 8+3+1 в журнале. AC-3: ✓ tests/test_renar_clause_reactive_adapt.py::test_an_adapt_that_grows_a_verdict_is_still_not_an_ar и tests/test_renar_clause_reactive_adapt.py::test_the_shape_is_the_standards_scalar_mandatory_fields; RENAR-CONFORMANCE.yaml v14 replaces CFM-2026-09-03-tausik@v13 (tests/test_renar_manifest_chain.py::test_the_committed_manifest_chain_resolves — живая цепь по git). AC-4: ✓ pwsh докстринг измеренный; docs/{en,ru}/enforcement-coverage.md остаток; CHANGELOG.md + CHANGELOG.ru.md синхронно; ревью на починку L3 #24 (changes_requested) -> починка -> L3 #25 approved; bootstrap --ide all выполнен, verify #2023 после него; память #547, #548 до done. Root cause (missing-validation): охранник счётчиков знал не все формы, а инвентарь носителей числа шёл только через него; цепь манифеста строилась из даты, а тест проверял форму строки, не разрешимость ссылки. Prevention: grep по старому числу + проба «вернул старое — красный» на каждую форму (память #547); ссылка на предшественника — из его id, живой тест по git (память #548). Domain: три документа и mcp.md несут 128/121 под охраной; цепь манифеста разрешима; update не обнуляет stale пустой строкой.
- 2026-09-04T09:21:26Z [implementation] — AC-1: ✓ tests/test_gen_doc_constants.py::test_scan_mcp_counts_sees_the_forms_review_208_found_blind (7 форм) и tests/test_gen_doc_constants.py::test_scan_mcp_counts_accepts_the_same_forms_when_right; три возврата 124 в документы -> --check exit 1 (журнал); docs/mcp.md 117 -> 121 с шаблоном. AC-2: ✓ tests/test_hierarchy_update.py::TestUpdate::test_an_empty_string_is_refused_and_writes_nothing, tests/test_hierarchy_update.py::TestStaleness::test_a_task_created_in_the_same_second_as_the_edit_is_not_counted, tests/test_hierarchy_update.py::TestCallers::test_stale_over_zero_is_a_filter_and_no_flag_is_none; импорт в верхнем блоке; entity_type задокументирован. Negative: пустые строки — отказ без события; мутации 8+3+1 в журнале. AC-3: ✓ tests/test_renar_clause_reactive_adapt.py::test_an_adapt_that_grows_a_verdict_is_still_not_an_ar и tests/test_renar_clause_reactive_adapt.py::test_the_shape_is_the_standards_scalar_mandatory_fields; RENAR-CONFORMANCE.yaml v14 replaces CFM-2026-09-03-tausik@v13 (tests/test_renar_manifest_chain.py::test_the_committed_manifest_chain_resolves — живая цепь по git). AC-4: ✓ pwsh докстринг измеренный; docs/{en,ru}/enforcement-coverage.md остаток; CHANGELOG.md + CHANGELOG.ru.md синхронно; ревью на починку L3 #24 (changes_requested) -> починка -> L3 #25 approved; bootstrap --ide all выполнен, verify #2023 после него (cache HIT после повторного bootstrap); память #547, #548 до done. Root cause (missing-validation): охранник счётчиков знал не все формы, а инвентарь носителей числа шёл только через него; цепь манифеста строилась из даты, а тест проверял форму строки, не разрешимость ссылки. Prevention: grep по старому числу + проба «вернул старое — красный» на каждую форму (память #547); ссылка на предшественника — из его id, живой тест по git (память #548). Domain: три документа и mcp.md несут 128/121 под охраной; цепь манифеста разрешима; update не обнуляет stale пустой строкой.
- 2026-09-04T09:21:42Z [done] — ПРИЗНАНИЕ ПРИ ЗАКРЫТИИ: COMPLEXITY UNDERSTATED — заявлено medium, тронуто 20 несущих файлов из 25 (complex). Второй раз за смену, пятая смена подряд по #523. Причина: задача-долг по ревью росла вторым кругом (ревью на починку добавило цепь манифеста, fixer, два mcp.md, новый тестовый файл) — сложность задачи по находкам ревью оценивать ПОСЛЕ ревью на починку нельзя, значит заводить как complex сразу, если находок больше трёх и они в разных подсистемах.
