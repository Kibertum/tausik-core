---
slug: kb-global-write
title: "Запись в общую базу: флаг global у memory, decide, snippet"
status: done
epic: shared-knowledge
story: kb-global
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/knowledge_write.py"
  - "scripts/knowledge_db.py"
  - "scripts/service_knowledge.py"
  - "scripts/service_decide.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_cli_snippet.py"
  - "tests/test_knowledge_write.py"
  - "tests/test_snippet_brain_extract.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/service_knowledge.py"
  - "scripts/knowledge_db.py"
  - "scripts/knowledge_write.py"
  - "scripts/service_decide.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_snippet.py"
  - "tests/test_knowledge_write.py"
  - "tests/test_snippet_brain_extract.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-02T15:21:59Z"
---

## Goal

Флаг --global у команд memory add, decide и работы со сниппетами направляет запись в общую базу вместо проектной. Ничего не спрашивать интерактивно: явный флаг и всё. Запись сохраняет пометку проекта-источника — на своей машине скрывать нечего, и это пригодится для ранжирования и для будущего авто-повышения. Скраббер здесь НЕ нужен: приватность переезжает на границу выгрузки в Notion.

## Acceptance Criteria

1. Флаг --global у memory add, decide и работы со сниппетами направляет запись в общую базу; без флага запись идёт в проектную. Тест проверяет обе ветки.
2. Флаг не запускает интерактивный диалог — маршрут определяется только явным флагом.
3. Запись в общую базу сохраняет пометку проекта-источника.
4. Скраббер на этом пути не вызывается (приватность переезжает на границу публикации в Notion).
5. НЕГАТИВНЫЙ СЦЕНАРИЙ — отказ записи в общую базу НЕ вырождается в тихую запись в проектную. Если общая база недоступна (TAUSIK_HOME указывает на путь, куда нельзя писать), команда завершается ВНЯТНОЙ ошибкой, называющей путь, И в проектной базе не появляется ничего. Тест проверяет ОБЕ половины: и что ошибка поднята, и что проектная база не изменилась. Основание: тихий откат на проектную базу означал бы, что пользователь считает знание общим, а оно осталось в одном репозитории — дефект, невидимый в момент совершения.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; записи снова только в проектную БД

## Journal

- 2026-08-02T15:21:56Z [implementation] — AC verified: 1. ✓ ФЛАГ МАРШРУТИЗИРУЕТ, ОБЕ ВЕТКИ ПРОВЕРЕНЫ. --global у memory add и decide, --scope global у snippet extract (вписан в УЖЕ СУЩЕСТВУЮЩЕЕ понятие назначения команды, а не вторым флагом рядом). Пары тестов в TestTheFlagRoutesTheWrite: без флага запись в проектной и НЕТ в общей; с флагом наоборот, причём каждый тест утверждает ОБЕ половины (в общей появилось И в проектной пусто), иначе дубль прошёл бы незамеченным. ОТДЕЛЬНО добавлен test_a_task_linked_decision_still_honours_the_flag — единственная комбинация, где гарантия держится ПОРЯДКОМ ветвей, а не структурой: у decide есть правило «решение с task_slug всегда локальное», и ветка to_global стоит ВЫШЕ него. Найдено ревью, было непокрыто. 2. ✓ БЕЗ ДИАЛОГА. Маршрут определяется только флагом. Подсказка об универсальности на общем пути НЕ вызывается (test_the_universality_hint_does_not_fire_on_the_shared_path) — она задаёт вопрос, на который флаг уже ответил. КОНТРОЛЬНЫЙ тест test_the_local_path_still_fires_it с ТЕМ ЖЕ монкейпатчем требует срабатывания на локальном пути: без него отсутствие вызова ничего бы не доказывало. Ревью независимо проверило механику перехвата и подтвердило, что патч ловит реальный путь (импорт локальный, резолвится в момент вызова). 3. ✓ ПОМЕТКА ИСТОЧНИКА. origin_project — АБСОЛЮТНЫЙ корень проекта, выведенный из ручки .tausik, а не из cwd: test_origin_survives_being_run_from_a_subdirectory доказывает, что запуск из подкаталога атрибутирует правильно. Абсолютный потому, что базовые имена сталкиваются (core, server, api). origin_slug несёт задачу. 4. ✓ СКРАББЕР НЕ ВЫЗЫВАЕТСЯ. test_content_reaches_the_shared_store_verbatim подменяет brain_scrubbing.scrub на pytest.fail и пишет строку, похожую на токен, — содержимое доезжает дословно. 5. ✓ НЕГАТИВНЫЙ СЦЕНАРИЙ (добавлен мной в AC — гейт QG-0 справедливо не пустил задачу без него). Отказ общей записи НЕ вырождается в тихую проектную. Три теста: для памяти, для решений, и на ТЕКСТ ошибки. Каждый проверяет ОБЕ половины — что ServiceError поднят И что проектная база пуста, потому что любая половина в одиночку пропустила бы сломанную реализацию. Недоступность смоделирована путём, чей родитель есть ФАЙЛ: работает на всех платформах, в отличие от chmod, который root игнорирует, а Windows не соблюдает. CHANGELOG.md и зеркало CHANGELOG.ru.md — прозаическая запись, включая честную оговорку о том, чего обоснование про скраббер НЕ покрывает. ПРОБЫ ФАЛЬСИФИЦИРУЕМОСТИ, ПОТЕСТОВО, обратимыми правками кода: • тихий откат (try/except вокруг общей записи) -> 1 failed, красный РОВНО test_an_unwritable_home_raises_and_leaves_the_project_untouched; • маршрутизация снята (if False) -> 6 failed: роутинг, атрибуция, скраббер, откат; • ветка to_global у decide удалена -> 3 failed, включая НОВЫЙ test_a_task_linked_decision_still_honours_the_flag; • после каждого восстановления зелено. ПРОВЕРКА ЗАПУСКОМ АРТЕФАКТА (память #346), настоящий CLI после bootstrap: memory add --global и decide --global записали в общую базу по TAUSIK_HOME, origin = [вычеркнуто: local-path], PRAGMA user_version = 1; в проектной базе последней записью осталась #363, то есть дубля нет. МУЛЬТИАГЕНТНОЕ РЕВЬЮ (три ревьюера, разные линзы) — ВСЕ ПОДТВЕРЖДЁННЫЕ НАХОДКИ ЗАКРЫТЫ ИЛИ ЗАВЕДЕНЫ: Починено здесь: (а) права на хранилище сужены до владельца при создании, по образцу crypto_keys для ключа подписи; (б) докстринг service_decide.record утверждал «записывает локально», хотя с флагом не записывает локально ВООБЩЕ — переписан; (в) докстринг, Usage и help у snippet extract описывали только brain — обновлены; (г) справка --global у memory add и decide теперь предупреждает об отсутствии вычистки; (д) тест на порядок ветвей добавлен; (е) test_unsupported_scope переписан на ЗАМЫСЕЛ (отказ называет все рабочие области), а не на прежнюю фразу, плюс добавлен тест ветки --scope global ЧЕРЕЗ диспетчер CLI, а не мимо него. ГЛАВНОЕ, ЧТО ПРИЗНАНО: моё обоснование «та же зона доверия» подменяло «тот же пользователь ОС» на «та же зона конфиденциальности». Путь этого репозитория содержит имя заказчика; один человек ведёт несколько клиентов из одной домашней папки, поэтому общая база пересекает периметр заказчика ПО ПОСТРОЕНИЮ, без всякого экспорта. Обоснование в коде и в обоих CHANGELOG переписано так, чтобы называть и что оно покрывает, и чего не доказывает. Заведены четыре задачи: export-of-the-shared-store-must-scrub-or-stay-local (БЛОКЕР выгрузки — план бэкапа на S3 опровергает довод «не покидает машину»), memory-block-injects-multiline-text-across-projects (БЛОКЕР шага 3), origin-project-stores-client-names-readable-from-every-project, tausik-home-is-unvalidated-and-may-point-into-git-or-cloud-sync. Domain: осмысленно вне тестов. Общая база — файл, который человек носит между проектами; проверено живым CLI, а не только pytest. Отказ смоделирован реальной причиной (недоступный путь), а не подменой функции. Права 0600/0700 — наблюдаемое свойство файловой системы. Полный pytest: 6584 passed, 24 skipped, 0 failed, 0 errors (676s). ruff check — All checks passed. ruff format — already formatted. mypy — Success: no issues found in 296 source files. bootstrap --ide all прогнан, drift отсутствует.
