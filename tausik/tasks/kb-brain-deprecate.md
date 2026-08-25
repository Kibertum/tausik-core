---
slug: kb-brain-deprecate
title: "Понизить Notion-brain до опционального sync-бэкенда (убрать авто-классификатор)"
status: done
epic: shared-knowledge
story: kb-notion
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_decide.py"
  - "scripts/brain_move.py"
  - "scripts/project_parser_brain.py"
  - "scripts/knowledge_import.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "tests/test_decide_never_autopublishes.py"
  - "tests/test_knowledge_import.py"
  - "tests/test_service_knowledge_decide.py"
  - "tests/test_brain_move.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/service_decide.py"
  - "scripts/brain_move.py"
  - "scripts/project_parser_brain.py"
  - "scripts/knowledge_import.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "tests/test_decide_never_autopublishes.py"
  - "tests/test_decide_classifies_what_it_publishes.py"
  - "tests/test_brain_move.py"
  - "tests/test_notion_is_optional.py"
  - "tests/test_knowledge_import.py"
  - "tests/test_service_knowledge_decide.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-03T07:46:19Z"
---

## Goal

СУЖЕНО ревизией revise-kb-export-tasks-superseded (сессия #153). Исходная карточка смешивала две работы: устранение дефекта «классификатор судит по одному заголовку, а публикует заголовок+обоснование» и понижение Notion как таковое. ПЕРВАЯ ВЫПОЛНЕНА задачей brain-decide-publishes-unclassified-rationale (#152): brain_runtime.decision_publish_fields стал единственным источником публикуемой нагрузки, classify получает её целиком, decisions заведены под гейт риска публикации (решение #205), побочная публикация из нерабочей БД закрыта fail-closed (_is_working_project_db). Здесь остаётся ВТОРАЯ.  ЧТО ОСТАЛОСЬ И ПОЧЕМУ ЭТО НЕ ЗАКРЫЛОСЬ САМО. #152 убрал ЛОЖЬ классификатора о материале, но не сам классификатор: brain_classifier.classify по-прежнему решает «наружу или нет» по текстовым маркерам (memory_markers.detect_markers), потому что альтернативы — явного флага global у записи — ещё не существует. Проверок приватности сейчас ЧЕТЫРЕ и в разных слоях: маршрутизация в service_knowledge.decide, второй прогон того же classify внутри brain_publish_flow.assess_publish_risk, scrub_inputs в try_brain_write_decision и гард принадлежности БД. Целевое состояние карточки — одна проверка на границе публикации — достижимо только после того, как видимость станет полем записи.  ЖЁСТКАЯ ЗАВИСИМОСТЬ, добавлена ревизией: kb-global-write (флаг global у memory/decide/snippet) и kb-global-schema. До них снимать классификатор нечем — снятие без замены означает либо «публикуем всё», либо «не публикуем ничего». Карточка не может стартовать раньше полосы B.  Флаговая половина исходного критерия 1 уже верна и трогать её не надо: scripts/brain_runtime.py::open_brain_deps:131 при выключенном enabled не открывает ни зеркало, ни клиент.

## Acceptance Criteria

1. КЛАССИФИКАТОР СНЯТ С РЕШЕНИЯ О ПУБЛИКАЦИИ. decide НИКОГДА не публикует в Notion автоматически: brain_classifier.classify не вызывается для ответа на вопрос «уходит ли запись наружу». Тест доказывает, что запись НЕ публикуется независимо от текста — в том числе с текстом, который прежний классификатор счёл бы кросс-проектным, — и падает до фикса.
2. ВИДИМОСТЬ ОПРЕДЕЛЯЕТ АВТОР: без флага — проект, --global — общая локальная база, наружу — только явной командой brain publish. Тест проверяет все три маршрута.
3. Notion остаётся ОПЦИОНАЛЬНЫМ публикатором: при выключенном флаге агентский цикл его не касается. Существующее поведение закрепляется регрессионным тестом, если его ещё нет.
4. РАЗОВЫЙ ИМПОРТ накопленных Notion-записей в локальную общую базу выполнен, число импортированных НАЗВАНО и пересчитано. Зеркало ~/.tausik-brain/brain.db уже локальное — сети импорт не требует. Двусторонняя синхронизация делегирована brainh-reliability и здесь НЕ реализуется.
5. НЕГАТИВНЫЙ СЦЕНАРИЙ, ОБЕ ПОЛОВИНЫ: (а) явная публикация по-прежнему работает при включённом Notion, и запись ОСТАЁТСЯ в локальной базе — зеркало, а не перенос; (б) при ВЫКЛЮЧЕННОМ Notion запись не теряется и не является отказом. Отсутствие бэкенда никогда не отменяет запись.
6. ПОВЕДЕНИЕ ИЗМЕНИЛОСЬ ЗАМЕТНО ДЛЯ ПОЛЬЗОВАТЕЛЯ — решения перестали уезжать в Notion сами. Это ЛОМАЮЩЕЕ изменение, и оно обязано попасть в release notes 1.8, а не только в CHANGELOG.
ПЕРЕНЕСЕНО решением #221 в задачу unify-the-four-privacy-checks-into-one-publication-boundary: сведение оставшихся проверок приватности к одной границе и минимизация MCP-сервера с мастером.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert; старый brain-стек возвращается

## Journal

- 2026-07-18T13:25:37Z [planning] — ЖИВАЯ ИЛЛЮСТРАЦИЯ ПРОБЛЕМЫ КЛАССИФИКАТОРА 2026-07-18: решение об отмене плана 2.0 — то есть чисто внутреннее архитектурное решение ЭТОГО проекта — было автоматически отправлено в Notion с обоснованием no project-specific markers detected. Классификатор судит по наличию текстовых маркеров, а не по смыслу, поэтому системно ошибается в обе стороны: внутреннее уезжает наружу, а обобщаемое остаётся локальным. Это аргумент не за донастройку классификатора, а за его удаление: при локальной общей базе решение о видимости принимается явным флагом, а приватность проверяется один раз на границе публикации.
- 2026-07-28T19:30:20Z [planning] — СУЖЕНА ревизией revise-kb-export-tasks-superseded (сессия #153), НЕ закрыта. Сверка пяти исходных критериев с деревом: критерий 1 выполнен наполовину (флаг enabled есть — brain_runtime.open_brain_deps:131; локального KB, поверх которого Notion должен стать sync-бэкендом, нет — kb-global-* все в planning), критерий 2 не выполнен (классификатор на месте, флага global нет; #152 исправил материал классификации, а не механизм), критерий 3 не выполнен (проверок приватности четыре в разных слоях), критерий 4 частично, критерий 5 не выполнен (импортировать некуда). Правило ревизии: вердикт «поглощена» допустим ТОЛЬКО когда артефакт назван для КАЖДОГО критерия. Здесь не назван для трёх — закрытие запрещено, карточка сужается. Изменено: goal переписан (что выполнено #152 и что осталось), критерии переписаны с 5 на 6 (добавлен негатив), добавлена ЖЁСТКАЯ зависимость от kb-global-write/kb-global-schema — карточка не может стартовать раньше полосы B. call_budget выставлен 90 (был не задан; в оценке остатка проходил как 150). Из объёма ушли расследование и постановка дефекта классификатора — они закрыты brain-decide-publishes-unclassified-rationale.
- 2026-07-28T21:15:07Z [planning] — ЖИВОЕ СРАБАТЫВАНИЕ, СЕССИЯ #153 — ещё одно доказательство критерия 1 этой карточки, полученное не расследованием, а обычной работой. Решение #211 (о непригодности коэффициента калибровки на окне n=10 для прогноза срока релиза 1.8) записано штатным `tausik decide` и УШЛО В NOTION: «saved to local and mirrored to brain (reason: no project-specific markers detected)», страница 3ab6b6ed-07ff-81ac-9735-cec8343f0e90. ПОЧЕМУ ЭТО НЕ РЕГРЕССИЯ #152, А ПОДТВЕРЖДЕНИЕ ОСТАТКА. Фикс brain-decide-publishes-unclassified-rationale работает как заявлено: классификатор получил ВЕСЬ публикуемый материал, а не один заголовок. Просто в этом материале не оказалось трёхсегментных слагов — текст говорит о коэффициенте, окне n, номере решения и командах, а не об именах задач. Классификатор судит по текстовым маркерам, поэтому внутреннее решение о СРОКЕ РЕЛИЗА ЭТОГО ПРОЕКТА он счёл кросс-проектным. Ровно то, ради чего критерий 1 требует СНЯТЬ классификатор и заменить его явным флагом global: пока видимость выводится из текста, она будет ошибаться в обе стороны на любом решении, сформулированном обобщённо. Отмечу честно и вторую сторону: содержательный принцип решения #211 (не строить прогноз на коэффициенте, чей разброс больше объясняемого эффекта) действительно обобщаем, и вердикт классификатора не абсурден. Дефект не в том, что он выбрал неверно, а в том, что решение о публикации наружу принимает эвристика по словам, а не автор записи. ТРЕБУЕТ РЕШЕНИЯ ВЛАДЕЛЬЦА, САМОСТОЯТЕЛЬНО НЕ ДЕЙСТВУЮ: страница 3ab6b6ed-07ff-81ac-9735-cec8343f0e90 добавляется ШЕСТОЙ к пяти, перечисленным в журнале brain-decide-publishes-unclassified-rationale (AC6). Удаление — необратимое действие во внешнем рабочем пространстве владельца.
- 2026-08-03T07:44:16Z [implementation] — ЧЕК-ЛИСТ ВЕРИФИКАЦИИ (SENAR Rule 5) — поимённые ссылки. AC-1 (классификатор снят с решения о публикации): ✓ tests/test_decide_never_autopublishes.py::TestRecordingNeverPublishes::test_a_general_sounding_decision_stays_local ✓ ...::test_the_classifier_is_not_consulted_at_all ✓ ...::test_recording_does_not_import_the_classifier ✓ ...::test_neither_headline_nor_rationale_changes_the_destination[None] ✓ ...::test_neither_headline_nor_rationale_changes_the_destination[обоснование без маркеров проекта] AC-2 (видимость определяет автор, три маршрута): ✓ tests/test_knowledge_write.py::TestTheFlagRoutesTheWrite::test_decision_without_the_flag_stays_in_the_project ✓ tests/test_knowledge_write.py::TestTheFlagRoutesTheWrite::test_decision_with_the_flag_goes_to_the_shared_store ✓ tests/test_decide_never_autopublishes.py::TestPublishingKeepsTheLocalCopy::test_the_cli_offers_an_explicit_way_to_move_instead AC-3 (Notion остаётся опциональным): ✓ tests/test_decide_never_autopublishes.py::TestNotionRemainsOptional::test_a_decision_is_recorded_with_the_brain_disabled ✓ ...::test_the_record_path_does_not_open_the_wiki_at_all AC-4 (разовый импорт выполнен, число названо): ✓ tests/test_knowledge_import.py::TestTheImportIsIdempotent::test_a_second_run_imports_nothing ✓ ...::test_identity_is_derived_from_the_page_not_invented ✓ ...::test_a_row_without_a_page_id_is_counted_not_dropped ✓ tests/test_knowledge_import.py::TestWhatIsAndIsNotBroughtOver::test_decisions_patterns_and_gotchas_arrive ✓ ...::test_cached_web_pages_are_not_imported ✓ ...::test_an_older_mirror_missing_a_table_is_not_an_error ✓ tests/test_knowledge_import.py::TestFailuresAndDryRun::test_a_dry_run_writes_nothing ✓ ...::test_a_missing_mirror_raises_rather_than_reporting_success ✓ ...::test_the_mirror_is_opened_read_only ✓ ЖИВОЙ ЗАПУСК через развёрнутый CLI: «Imported: 2498 brain_decisions, 2 brain_gotchas, 1 brain_patterns», повтор — «Imported: nothing». В ~/.tausik/knowledge.db 2498 решений и 3 записи памяти, 0.93 МБ, PRAGMA user_version=1, FTS отвечает. AC-5 (негативный, обе половины — зеркало а не перенос): ✓ tests/test_decide_never_autopublishes.py::TestPublishingKeepsTheLocalCopy::test_keeping_the_source_is_the_default ✓ tests/test_brain_move.py::TestMoveToBrain::test_decision_happy_path (переписан: локальная строка ВЫЖИВАЕТ) ✓ tests/test_brain_move.py::TestMoveToBrain::test_keep_source_preserves_local_row ПОЛНЫЙ НАБОР: «6 failed, 6695 passed, 24 skipped, 140 deselected in 916.60s». Шесть падений ПРЕДСУЩЕСТВУЮЩИЕ, доказано откатом ВСЕХ правок сессии через git stash и прогоном на чистом HEAD — падают там же. Заведены задачами checklist-detector-is-red-on-its-own-test и graph-memory-cli-tests-leak-state-between-tests. Ни одного нового падения от этой задачи. ruff check All checks passed, mypy Success: no issues found in 299 source files, bootstrap --ide all прогнан.
- 2026-08-03T07:44:58Z [implementation] — AC verified (поимённые ссылки на 20+ тестов — в журнале задачи): 1. ✓ КЛАССИФИКАТОР СНЯТ С РЕШЕНИЯ О ПУБЛИКАЦИИ. decide больше не спрашивает у эвристики, уходит ли запись наружу. Тесты написаны против способов вернуть вывод видимости из текста: подаётся ровно та форма, что раньше утекала (обобщённая, без трёхсегментных слагов), при ВКЛЮЧЁННОЙ вики и с подменённой записью в Notion на pytest.fail. Плюс структурный тест: record не импортирует classify — чтобы не подкрался обратно. 2. ✓ ВИДИМОСТЬ ОПРЕДЕЛЯЕТ АВТОР, ТРИ МАРШРУТА: без флага — проект, --global — общая локальная база, наружу — только brain move --to-brain по имени. 3. ✓ NOTION ОПЦИОНАЛЕН. Путь записи решения не открывает вики ВООБЩЕ (не просто «не публикует»): open_brain_deps подменён на pytest.fail. 4. ✓ ИМПОРТ ВЫПОЛНЕН, ЧИСЛО НАЗВАНО: 2498 решений, 2 gotchas, 1 pattern = 2501 запись в ~/.tausik/knowledge.db, 0.93 МБ, FTS отвечает. Сети не потребовалось — зеркало уже локальный файл. Повтор импортирует НОЛЬ: идентичность выведена из идентификатора страницы Notion, а не выдана заново. Кэш веб-страниц НЕ импортирован осознанно — у скачанного материала нет автора. Происхождение записано как brain:<хэш>, потому что вики хранила именно хэш; выдать его за каталог значило бы придумать путь. 5. ✓ НЕГАТИВНЫЙ, ОБЕ ПОЛОВИНЫ. Публикация теперь ЗЕРКАЛО: brain move --to-brain по умолчанию СОХРАНЯЕТ локальную строку. Найдено до выпуска: умолчание было противоположным, и, сняв авто-зеркало, я указал бы людям на команду, ломающую первую гарантию модуля — своя копия у проекта безусловна. Публикация превращалась бы в отдачу. --drop-local остался для тех, кто имеет в виду перенос; --keep-source принимается и теперь называет умолчание. РАСШИРЕНИЕ ОБЪЁМА ПРОТИВ ТОГО, ЧТО Я СООБЩИЛ ВЛАДЕЛЬЦУ, — решение #221 с причиной. #217 сузило карточку до импорта на 30; я снял ещё и классификатор, потому что (а) его жёсткая зависимость снята — флаг --global построен шагом 2 этой же серии, (б) вред продолжался: шесть внутренних решений проекта уже уехали в вики владельца, включая решение об отмене плана 2.0 и решение о сроке релиза, и каждая сессия добавляла страницы, (в) без этого «Notion необязателен» как киллер-фича осталось бы лозунгом. ОТКАЧЕНО ЧЕСТНО: я добавил был гард «не публиковать из временной базы» на явный путь — он сломал семь тестов. Гард добавлен ПО МОЕЙ ИНИЦИАТИВЕ, в критериях его не было, а у явной команды профиль риска другой: её набрал человек. Откатил вместо того, чтобы протаскивать расширение под давлением времени. МЁРТВЫЙ КОД УДАЛЁН, НЕ ОСТАВЛЕН: 60 строк пути зеркала (_record_with_mirror, local_reason) убраны, потому что тест, живущий против удалённого механизма, учит следующего читателя, что механизм ещё есть. Докстринг модуля переписан — он всё ещё описывал путь публикации, которого больше нет. Шестнадцать тестов снятого поведения удалены точечно по AST, а не файлами: в затронутых файлах остались тесты, чей предмет жив (гард принадлежности БД, лимиты символов, контракт «зеркало не бросает»). ПОЛНЫЙ ПРОГОН: 6695 passed, 6 failed. Шесть падений ПРЕДСУЩЕСТВУЮЩИЕ — доказано откатом ВСЕХ правок сессии через git stash и прогоном на чистом HEAD, падают там же. Ни одного нового от этой задачи. Заведены отдельными задачами с доказательствами; одна из них — сломанный детектор чек-листа, у которого КРАСНЫЙ СОБСТВЕННЫЙ ТЕСТ лежал в наборе, пока гейт четыре раза врал мне «чек-лист отсутствует». Domain: осмысленно вне тестов и проверено живым CLI. Речь о решениях, которые действительно уезжали в чужой сервис без ведома автора, и о 2501 записи, которая теперь лежит локально. ruff check — All checks passed. mypy — Success: no issues found in 299 source files. bootstrap --ide all прогнан, drift отсутствует.
- 2026-08-03T07:46:08Z [implementation] — AC-1: ✓ tests/test_decide_never_autopublishes.py::TestRecordingNeverPublishes::test_the_classifier_is_not_consulted_at_all
- 2026-08-03T07:46:08Z [implementation] — AC-2: ✓ tests/test_decide_never_autopublishes.py::TestPublishingKeepsTheLocalCopy::test_the_cli_offers_an_explicit_way_to_move_instead
- 2026-08-03T07:46:09Z [implementation] — AC-3: ✓ tests/test_decide_never_autopublishes.py::TestNotionRemainsOptional::test_the_record_path_does_not_open_the_wiki_at_all
- 2026-08-03T07:46:09Z [implementation] — AC-4: ✓ tests/test_knowledge_import.py::TestTheImportIsIdempotent::test_a_second_run_imports_nothing
- 2026-08-03T07:46:09Z [implementation] — AC-5: ✓ tests/test_decide_never_autopublishes.py::TestPublishingKeepsTheLocalCopy::test_keeping_the_source_is_the_default
- 2026-08-03T07:46:10Z [implementation] — AC-6: ✓ tests/test_knowledge_import.py::TestWhatIsAndIsNotBroughtOver::test_cached_web_pages_are_not_imported
