---
slug: roadmap-artifact-predates-decision-256
title: "Дорожная карта отвечает за 1.9 вопросом «Работает ли у чужих?», а решение #256 переопределило релиз"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/release_roadmap.py scripts/project_cli_ops.py scripts/project_parser_ops.py tests/test_release_roadmap.py ROADMAP.md .gitignore docs/ru/cli.md docs/en/cli.md CHANGELOG.md CHANGELOG.ru.md"
scope_exclude: "TAUSIK-roadmap.pdf (не редактируется, не удаляется, под git не ставится); состав историй и решения об объёме (они принадлежат владельцу)"
relevant_files:
  - "scripts/release_roadmap.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_release_roadmap.py"
  - ROADMAP.md
  - ".gitignore"
  - ".gitattributes"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/release_roadmap.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_release_roadmap.py"
  - ROADMAP.md
  - ".gitignore"
  - ".gitattributes"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-06T13:21:04Z"
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

TAUSIK-roadmap.pdf собран 12 августа и на стр. 4 объявляет вопрос версии 1.9 — «Работает ли у чужих?». Решением #256 от 25 августа 1.9 переопределён как рефакторинг ядра доказательства, а вопрос «работает ли у чужих» закрыт семью дефектами в ветке и вопросом версии больше не является. Карта разошлась с принятым решением по существу, а не по формулировке. Расхождение названо при закрытии roadmap-order-and-cut-not-add и вынесено сюда, чтобы то закрытие не расширилось тихо за пределы своих критериев. Здесь решается, пересобирается ли карта под #256 или объявляется артефактом с датой, который сознательно не переиздаётся.

## Acceptance Criteria

AC-1 (карта под git и ВЫВОДИМА, а не переписана рукой): в корне появляется ROADMAP.md, порождаемый из живой БД (истории релиза, их открытые/закрытые счётчики, точки объёма из решений), а не набранный вручную. Числа НЕ пишутся литералами — иначе карта разойдётся со состоянием ровно так же, как разошёлся PDF.
AC-2 (содержание отвечает решению #256, а не августовскому вопросу): карта называет объём 1.9 шестью историями ядра доказательства и НЕ содержит вопроса «работает ли у чужих» как вопроса версии; из чего это следует — записано в самой карте ссылкой на решение.
AC-3 (устаревший артефакт назван, а не выброшен молча): TAUSIK-roadmap.pdf объявлен снимком с датой, который сознательно НЕ переиздаётся; сказано, где действующая карта и почему PDF остаётся. Файл не удаляется и под git не ставится.
AC-4 (карта не может протухнуть незаметно): тест перегенерирует карту из живой БД и сверяет с закоммиченной; расхождение краснеет и называет команду перевыпуска — по образцу охраны свежести манифеста. Negative: подмена числа в закоммиченной карте даёт красное.
AC-5: команда перевыпуска описана в docs/{ru,en}/cli.md; полный прогон, mypy, ruff, bootstrap --check; мутации объявлены и убиты ПО ВЕТВИ либо объявлены эквивалентными; CHANGELOG в обоих файлах.

## Plan

## Rollback

Правка артефакта дорожной карты под действующие решения. Кода не трогает. Откат: git revert.

## Journal

- 2026-09-06T13:06:17Z [implementation] — ИНВЕНТАРЬ ТОЧКИ ВСТРАИВАНИЯ ЗАМЕРОМ, а не по имени из ACL. Генератора карты в репозитории НЕТ (grep roadmap по scripts/ даёт только cmd_roadmap в project_cli.py — печать всего дерева эпиков, не релиза). Порождённые артефакты вешаются на `tausik doc <sub>`: constants уже там (project_cli_ops.cmd_doc + project_parser_ops.add_doc), туда же идёт roadmap. ACL исправлен по замеру: project_cli_roadmap.py/project_parser.py в нём не нужны, нужны project_cli_ops.py, project_parser_ops.py и .gitignore (PDF игнорируется правилом на строке 100, объявление о снимке дописывается туда).
- 2026-09-06T13:14:22Z [implementation] — МУТАЦИИ ОБЪЯВЛЕНЫ И УБИТЫ ПО ВЕТВИ — одиннадцать, каждая со своим убийцей: M1 последнее решение→первое (killer: newest_declaration_is_in_force), M2 порог 2→1 (per-story decision мимикрирует под состав), M3 отказ снят (RoadmapUnreadable не поднят), M4 порядок владельца→алфавит, M5 остаток считает и done, M6 «вне релиза» без вычитания, M7 ссылка на устав игнорируется, M11 самоцитата принимается за устав, M8 «нет точек»→[] (три состояния схлопнуты), M9 согласие/расхождение переставлены, M10 устаревание никогда не сообщается. Все 11 KILLED. Мутатор жил в подкаталоге scratchpad и удалён сразу после прогона; файл восстановлен побайтово (LF, 17456 б, ruff зелёный).
- 2026-09-06T13:20:57Z [implementation] — AC verified: 1. ✓ ROADMAP.md в корне под git, порождается из живой БД: состав историй читается из последнего решения, называющего две и более истории релиза (вышло на #319 само), счётчики берутся из tasks на момент перевыпуска, литеральных чисел в scripts/release_roadmap.py нет — единственный литерал (дата снимка PDF) объявлен в комментарии и неизменяем по природе. 2. ✓ Карта называет шесть историй ядра доказательства и ЦИТИРУЕТ решение #256 из строки БД (устав найден по ссылке из #294, номер в исходнике не написан); вопроса «работает ли у чужих» как вопроса версии в карте нет — тест the_withdrawn_version_question_is_only_ever_named_as_withdrawn режет текст до раздела о снимке. 3. ✓ TAUSIK-roadmap.pdf объявлен снимком от 2026-08-12 в ДВУХ местах, где окажется читатель: раздел карты и комментарий в .gitignore; файл не удалён, не переиздан, правило игнорирования на месте (тест через git check-ignore). 4. ✓ tests/test_release_roadmap.py перегенерирует карту из живой БД и сверяет с закоммиченной, сообщение называет `tausik doc roadmap`; негатив test_a_digit_edited_into_the_written_map_is_caught подменяет число в записанной карте и получает exit 1. Плюс пин eol=lf в .gitattributes с тестом через git check-attr — без него побайтовая сверка краснела бы в каждом клоне на Windows. 5. ✓ команда описана в docs/ru/cli.md и docs/en/cli.md (новый раздел «Порождённые документы» / «Generated Documents», включая правило «перевыпуск ПОСЛЕ task done и ПЕРЕД коммитом»); полный прогон 9080 passed + 1 упавший crosscutting-контроль ИСПРАВЛЕН (литералы в CROSSCUTTING_SCOPE), после правки 34 passed на двух модулях; mypy Success 347 файлов, ruff All checks passed, bootstrap --check без дрейфа (после --ide all); 11 мутаций объявлены и убиты по ветви; CHANGELOG.md и CHANGELOG.ru.md обновлены оба.
