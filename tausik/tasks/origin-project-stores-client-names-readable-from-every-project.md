---
slug: origin-project-stores-client-names-readable-from-every-project
title: "origin_project хранит абсолютный путь с именем заказчика, и он читается из любого другого проекта на машине"
status: done
epic: shared-knowledge
story: kb-global
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/knowledge_origin.py"
  - "scripts/knowledge_write.py"
  - "scripts/knowledge_db.py"
  - "scripts/knowledge_read.py"
  - "scripts/knowledge_export.py"
  - "scripts/knowledge_import.py"
scope_paths:
  - "scripts/knowledge_origin.py"
  - "scripts/knowledge_write.py"
  - "scripts/knowledge_read.py"
  - "scripts/knowledge_db.py"
  - "scripts/knowledge_export.py"
  - "scripts/knowledge_import.py"
  - "scripts/project_cli_snippet.py"
  - "tests/*"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/*"
  - "docs/ru/*"
scope_tools: []
depends_on: []
completed_at: "2026-08-03T18:21:33Z"
---

## Goal

Найдено ревью безопасности сессии #155. Находка бьёт в обоснование, которое я записал в kb-global-write, и я признаю подмену понятий: «тот же пользователь ОС» было выдано за «та же зона конфиденциальности», а это не одно и то же.

ЗАМЕР: knowledge_write.origin_project_root() кладёт абсолютный корень проекта в КАЖДУЮ запись КАЖДОГО типа. В этом репозитории он равен D:\\Work\\Kibertum\\clients\\<заказчик>\\..., то есть имя заказчика лежит в общей базе открытым текстом.

СЦЕНАРИЙ: агент, работающий в проекте клиента B, открывает ~/.tausik/knowledge.db — тот же файл, тот же пользователь ОС — и видит origin_project с путём клиента A. Никакого экспорта не требуется, достаточно чтения. В консалтинге и фрилансе периметр — это КЛИЕНТ, а не учётная запись ОС, и общая база пересекает его по построению.

ПОЧЕМУ НЕ ПРОСТО «ХРАНИТЬ ПСЕВДОНИМ»: origin нужен для пометки источника в выдаче (это критерий приёмки kb-global-read) и для будущего авто-повышения. Псевдоним без таблицы соответствия сделает пометку бесполезной, а таблица соответствия просто переносит ту же строку в другое место.

РАЗВИЛКА, решить явно: (а) хранить абсолютный путь, но на ЧТЕНИИ показывать только последний компонент — ограничивает случайное раскрытие, сохраняя данные для дедупликации; (б) хранить псевдоним плюс локальную таблицу соответствия, недоступную из других проектов; (в) принять риск ОСОЗНАННО и записать это в документацию и в предупреждение при первом --global.
Сюда же: source_file у сниппетов нормализовать к относительному пути от корня проекта, независимо от того, как звали detect.

## Acceptance Criteria

РАЗВИЛКА РЕШЕНА ЯВНО: ни (а), ни (б), ни (в), а четвёртый вариант — origin_project хранит НЕОБРАТИМУЮ метку "<basename>@<fp8>", где fp8 — первые 8 hex sha256 абсолютного корня. Он снимает возражение против (б): таблица соответствия НЕ нужна, потому что проект пересчитывает свой отпечаток сам и узнаёт "мою" запись без словаря. Он сильнее (а): (а) чинит только ОТОБРАЖЕНИЕ, а данные в покое (sqlite3 напрямую, export, backup) продолжают называть заказчика.

AC1: knowledge_write больше НЕ записывает абсолютный путь. Тест: запись из проекта, чей корень содержит имя каталога-заказчика, даёт origin_project без разделителей пути и без этого имени.
AC2: столкновение имён различимо. Тест: два разных абсолютных корня с ОДИНАКОВЫМ basename дают РАЗНЫЕ origin_project.
AC3: метка воспроизводима и узнаваема из своего проекта. Тест: origin_label() дважды подряд из одного корня равны; отпечаток чужого корня не равен своему.
AC4: уже записанные строки чинятся, а не остаются. Одноразовая перезапись на открытии хранилища переводит абсолютные пути в метки. Тест: строка с абсолютным путём после открытия становится меткой; повторный прогон идемпотентен; строка, уже являющаяся меткой, не трогается.
AC5: три таблицы, а не одна. Тест: memory, decisions и snippets все три пишут метку и все три мигрируются (форма закрыта, конвенция #361).
AC6: source_file сниппета нормализован к пути относительно корня проекта. Тест: сниппет из абсолютного пути внутри проекта хранит относительный.
AC7: чтение не сломано. _short_origin на метке возвращает метку, старые тесты чтения зелёные.
AC8: докстринги, утверждавшие "store keeps the absolute root", переписаны — иначе нарратив разойдётся с кодом в тот же день (knowledge_write.py, knowledge_read.py, knowledge_export.py).
AC9 (НЕГАТИВНЫЙ/ГРАНИЧНЫЙ): вырожденный вход не роняет ни запись, ни миграцию и не выдаёт мусор. Тест: origin_project = NULL, пустая строка и путь ВНЕ любого проекта миграцией пропускаются без ошибки и без записи метки-пустышки; source_file вне корня проекта остаётся как был, а не превращается в цепочку "..\..\\" наружу; отсутствие .tausik-каталога при вычислении метки даёт ОШИБКУ с именем причины, а не тихую запись пустого origin.

## Plan

## Rollback

git revert коммита. Данные: перезапись origin_project НЕОБРАТИМА по построению (в этом её смысл — отпечаток невосстановим). Откат кода вернёт запись абсолютных путей для НОВЫХ записей, но уже обезличенные строки останутся метками; чтение и экспорт с метками работают, так что откат безопасен, просто не восстанавливает раскрытые пути. Если нужен именно откат данных — восстановить из export/backup общего хранилища до миграции.

## Journal

- 2026-08-03T17:49:42Z [implementation] — Развилка закрыта четвёртым вариантом: необоратимая метка <basename>@<fp8> вместо абсолютного корня. Возражение против псевдонима снято тем, что отпечаток ВЫЧИСЛИМ, а не назначен: словарь соответствия не нужен, проект узнаёт свою запись пересчётом. Схему НЕ версионирую: bump user_version заставил бы старый TAUSIK в других проектах отказаться открывать хранилище, а это шестое ломающее изменение в релизе, где их ровно пять и сходимость уже посчитана. Вместо этого — дешёвая перезапись на открытии.
- 2026-08-03T18:07:51Z [implementation] — Реализовано: scripts/knowledge_origin.py (метка, отпечаток, предикат уже-сделано, нормализация source_file); три точки записи в knowledge_write переведены на метку; redact_stored_origins в knowledge_db чинит уже записанные строки во ВСЕХ ТРЁХ таблицах на открытии, идемпотентно. Дополнительно закрыт смежный тихий отказ: origin_project_root опирался на find_tausik_dir, который при отсутствии проекта возвращает cwd/.tausik — запись проходила и ПРИПИСЫВАЛА строку каталогу оболочки. Теперь отказ с причиной. Тесты: новый tests/test_knowledge_origin.py (24 проверки) + пять чужих тестов, которые ЗАКРЕПЛЯЛИ старое поведение, переписаны с сохранением их цели (тест экранирования обратного слэша перенесён на source_file — поле, которое обратные слэши всё ещё носит). CHANGELOG EN+RU. Прогон целевых модулей: 118 passed.
- 2026-08-03T18:20:14Z [implementation] — Ревью (отдельный агент, adversarial) дало 1 critical, 1 high, 4 medium — принято пять из шести, шестое отклонено ИЗМЕРЕНИЕМ. CRITICAL: init_knowledge_schema стоял ВНЕ try/except, который закрывает соединение — до моей правки это было безопасно (только CREATE IF NOT EXISTS), redact_stored_origins сделал это ложным: занятый замок роняет с живым дескриптором, который вызывающий никогда не получит и не закроет, а он держит WAL для всех проектов. Починено, тест ПРОВЕРЕН на красноту без правки. HIGH: предикат 'содержит слэш' переписал бы свободный тег team/backend в backend@a52261f0 необратимо — теперь требуется АБСОЛЮТНЫЙ путь, и предикат кроссплатформенный (os.path.isabs не годится: на Linux он считает D:\Work\... относительным, а редактировать надо и записи с Windows). MEDIUM: два сообщения отказа в knowledge_export всё ещё утверждали про абсолютный путь в каждой строке — это ровно дефект 'нарратив против кода', который чинит этот релиз; переписаны на настоящую оставшуюся причину (свободный текст содержимого), и тест, ЗАКРЕПЛЯВШИЙ старое утверждение, теперь запрещает его. MEDIUM: добавлен realpath в канонизацию (8.3-имена, симлинки, junction); UNC против подключённого диска остаётся, названо в докстринге как известная граница. MEDIUM: сквозной тест на source_file в записанной строке, а не только на чистой функции. ОТКЛОНЕНО: 'скан на каждом открытии навсегда' — измерено: 20000 строк, полностью мигрированных, скан 1.84 мс против 0.76 мс DDL+FTS рядом и 3.98 мс всей установки схемы. Таблица-маркер добавила бы DDL и вторую вещь для согласования ради двух миллисекунд. Число записано в докстринг, чтобы не переспорить заново.
- 2026-08-03T18:21:30Z [implementation] — Развилка закрыта четвёртым вариантом: origin_project хранит метку basename@fp8. AC-1: ✓ tests/test_knowledge_origin.py::TestTheLabelItself::test_a_client_directory_does_not_survive_into_the_label AC-1: ✓ tests/test_knowledge_write.py::TestAttribution::test_origin_is_a_label_and_not_the_absolute_root AC-2: ✓ tests/test_knowledge_origin.py::TestTheLabelItself::test_two_projects_with_the_same_basename_stay_distinguishable AC-3: ✓ tests/test_knowledge_origin.py::TestTheLabelItself::test_the_same_root_always_fingerprints_the_same AC-3: ✓ tests/test_knowledge_origin.py::TestTheLabelItself::test_a_project_recognises_its_own_row_without_a_dictionary AC-3: ✓ tests/test_knowledge_origin.py::TestTheLabelItself::test_a_root_spelled_differently_is_still_the_same_project AC-4: ✓ tests/test_knowledge_origin.py::TestTheStoredRowsGetFixed::test_the_migration_reports_how_much_was_disclosed AC-4: ✓ tests/test_knowledge_origin.py::TestTheStoredRowsGetFixed::test_a_second_open_changes_nothing AC-4: ✓ tests/test_knowledge_origin.py::TestWhatCountsAsAlreadyDone::test_rewriting_is_idempotent AC-5: ✓ tests/test_knowledge_origin.py::TestTheStoredRowsGetFixed::test_every_table_is_migrated_not_just_the_first AC-6: ✓ tests/test_knowledge_origin.py::TestSnippetSourceFiles::test_a_path_inside_the_project_becomes_relative AC-6: ✓ tests/test_knowledge_origin.py::TestSnippetSourceFiles::test_the_stored_row_is_relative_and_not_just_the_helper AC-7: ✓ tests/test_knowledge_read.py::TestSharedRowsAreLabelledAndAddressless::test_a_legacy_absolute_origin_never_reaches_the_display AC-8: ✓ tests/test_knowledge_export.py::TestTheDestinationMustBeLocal::test_the_refusal_explains_why_rather_than_just_refusing AC-9: ✓ tests/test_knowledge_origin.py::TestTheStoredRowsGetFixed::test_a_row_with_no_origin_survives_the_migration AC-9: ✓ tests/test_knowledge_origin.py::TestWhatCountsAsAlreadyDone::test_values_that_disclose_nothing_are_left_alone AC-9: ✓ tests/test_knowledge_origin.py::TestWhatCountsAsAlreadyDone::test_a_free_text_value_that_merely_contains_a_separator_is_not_a_path AC-9: ✓ tests/test_knowledge_origin.py::TestSnippetSourceFiles::test_a_path_outside_the_project_does_not_climb_out_of_it AC-9: ✓ tests/test_knowledge_origin.py::TestTheLabelItself::test_a_root_with_no_basename_produces_a_well_formed_label AC-9: ✓ tests/test_knowledge_origin.py::TestAWriteThatCannotAttributeItselfFails::test_writing_from_outside_any_project_raises_and_names_why AC-9: ✓ tests/test_knowledge_origin.py::TestAWriteThatCannotAttributeItselfFails::test_nothing_was_written AC-9: ✓ tests/test_knowledge_origin.py::TestAFailedMigrationDoesNotLeakTheHandle::test_the_connection_is_closed_when_the_migration_raises AC8 частично прозаический: докстринги knowledge_write, knowledge_read, knowledge_export, knowledge_import переписаны; исполняемая часть — два сообщения отказа экспорта — закреплена тестом выше, который ЗАПРЕЩАЕТ вернуть старое утверждение. Прогоны: полный 6834 passed до правок ревью; после — целевые модули 124 passed, срез knowledge/mypy/ruff/docs 400 passed, mypy чист. Тест на утечку дескриптора проверен на красноту БЕЗ правки.
