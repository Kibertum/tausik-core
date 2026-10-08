---
slug: output-economy-mode-is-shipped-but-off-in-our-own-project
title: "Режим экономии вывода поставляется, а в нашем собственном проекте выключен — догфудинг нарушен"
status: done
epic: landscape-2026-h2
story: agent-output-discipline
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/economy_levers.py"
  - "tests/test_economy_levers_decided.py"
  - ".tausik/config.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
  - CLAUDE.md
  - AGENTS.md
scope_paths:
  - ".tausik/config.json"
  - "tests/"
  - "scripts/"
  - "docs/ru/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-07T19:02:44Z"
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

В bootstrap_templates.py живут два рычага: output_mode (сжимает ВЫВОД агента, значение caveman) и context_tier (размер впрыскиваемых ПРАВИЛ). В .tausik/config.json этого проекта НЕ УСТАНОВЛЕН НИ ОДИН — оба в умолчании, то есть выключены. Мы поставляем пользователю механизм экономии, которым сами не пользуемся, при заявленном принципе «Dogfooding: этот фреймворк — наш же пользователь». Задача: принять решение по каждому рычагу для ЭТОГО проекта и записать его, а не просто включить. Включение непусто: caveman меняет форму ответов во всех сессиях, а warn_output_mode_not_applied прямо предупреждает, что на уже забутстрапленном проекте флаг НИЧЕГО не меняет на диске — файл правил preserve-if-exists. Значит нужен либо явный путь применения к существующему файлу, либо честное сообщение о том, что требуется. Второй половиной задачи закрыть вопрос, почему собственный проект не проверяет собственные настройки: расхождение «поставляем, но не применяем» должно ловиться, а не обнаруживаться разбором поля.

## Acceptance Criteria

ЗАМЕР СМЕНЫ #229 ПЕРЕД РЕШЕНИЕМ. (1) Собственный вывод модели есть 71.6% прироста контекста (12 895 606 из 18 009 761 на 14 048 парах). (2) Но caveman сжимает только ПРОЗУ: из 16 287 948 символов вывода на текстовые блоки приходится 1 493 022 — 9.2%; 90.6% суть аргументы инструментов (команды Bash 7 274 197, содержимое Write 3 248 396, Edit 2 233 489), которые директива исключает как байт-точные, и ещё 6.5% — долговременная запись (журналы, передачи, решения, память), исключённая поимённо. Значит потолок caveman здесь 71.6% x 9.2% = 6.6%, а при разумном сжатии прозы на треть — около 2%. (3) ОБА РЫЧАГА ДЛЯ ЭТОГО ПРОЕКТА ИНЕРТНЫ: генератор правил preserve-if-exists, а наш CLAUDE.md написан руками (doctor: делит с шаблоном 0 заголовков из 14). Ключ context_tier=standard в нашем конфиге не читается никогда.

AC1. РЕШЕНИЕ ПО КАЖДОМУ РЫЧАГУ ЗАПИСАНО ЧИСЛОМ, А НЕ ВКУСОМ. Для output_mode и context_tier записано, включаем или нет, с измеренным потолком и с причиной. Решение фиксируется как decision, а не как комментарий в конфиге.
AC2. ПРИЧИНА РАСХОЖДЕНИЯ НАЗВАНА ВЕРНО. Догфудинг нарушен не тем, что «забыли включить», а тем, что механизм НЕ ДОСТАЁТ до написанного руками файла правил. Это записано прямо: иначе следующий читатель включит флаг и будет уверен, что сжатие работает, — ровно тот тихий no-op, о котором предупреждает warn_output_mode_not_applied.
AC3. РАСХОЖДЕНИЕ ЛОВИТСЯ, А НЕ ОБНАРУЖИВАЕТСЯ РАЗБОРОМ ПОЛЯ. Появляется детектор: для КАЖДОГО поставляемого рычага экономии наш собственный конфиг обязан нести явное решение — либо значение, либо запись в реестре сознательно неустановленных с причиной. Молчаливое умолчание запрещено.
AC4. РЕЕСТР НЕ ГНИЁТ (решение #335). Каждая запись реестра обязана называть рычаг, который РЕАЛЬНО существует в поставляемом коде; запись, не совпавшая ни с одним живым рычагом, краснит детектор. И обратно: рычаг, появившийся в коде и не названный ни значением, ни реестром, краснит детектор.
AC5 (НЕГАТИВНЫЙ СЦЕНАРИЙ). Детектор проверяется мутацией: выдуманный лишний рычаг в реестре даёт красное; рычаг без решения даёт красное; полный набор решений даёт зелёное. Отдельно: детектор не имеет права молча зеленеть при отсутствии конфига — отсутствие файла есть отсутствие решений, а не их наличие.

## Plan

## Rollback

git revert <commit>. Изменения: явные записи в .tausik/config.json (значения, которые и так были умолчанием), новый тест-детектор и текст решения. Поведение агента не меняется ни при откате, ни без него, потому что оба рычага для этого проекта инертны — генератор правил не переписывает существующий файл.

## Journal

- 2026-09-07T19:01:45Z [implementation] — AC-1 (решение по каждому рычагу числом): ✓ решение #340; ✓ tests/test_economy_levers_decided.py::TestThisProjectHasDecidedOnEveryLeverItShips::test_every_reason_says_something_a_reader_can_check — тест требует, чтобы КАЖДАЯ причина несла число, иначе это предпочтение, а не решение AC-2 (причина расхождения названа верно): ✓ tests/test_economy_levers_decided.py::TestOurOwnConfigMatchesWhatWeDecided::test_context_tier_is_present_but_recorded_as_inert — записано, что механизм НЕ ДОСТАЁТ до написанного руками файла правил, а не что забыли включить AC-3 (расхождение ловится, а не обнаруживается разбором поля): ✓ tests/test_economy_levers_decided.py::TestThisProjectHasDecidedOnEveryLeverItShips::test_no_lever_is_left_undecided AC-4 (реестр не гниёт, обе стороны решения #335): ✓ tests/test_economy_levers_decided.py::TestThisProjectHasDecidedOnEveryLeverItShips::test_no_registry_entry_names_a_lever_the_code_lost AC-4: ✓ tests/test_economy_levers_decided.py::TestTheShippedProofIsReadNotImported::test_each_lever_points_at_code_that_exists AC-5 (негативный сценарий, проверка мутацией): ✓ tests/test_economy_levers_decided.py::TestTheDetectorGoesRedWhenItShould::test_an_invented_registry_entry_is_caught AC-5: ✓ tests/test_economy_levers_decided.py::TestTheDetectorGoesRedWhenItShould::test_a_new_lever_nobody_decided_on_is_caught AC-5: ✓ tests/test_economy_levers_decided.py::TestTheDetectorGoesRedWhenItShould::test_a_missing_config_is_not_a_pass AC-5: ✓ tests/test_economy_levers_decided.py::TestTheDetectorGoesRedWhenItShould::test_a_malformed_config_is_not_a_pass_either Negative: детектор проверен на КРАСНОМ по каждой ветви, а не только на текущем зелёном состоянии. Выдуманный рычаг в реестре ловится. Рычаг, добавленный в код и никем не решённый, ловится. Дерево без кода рычага делает запись реестра устаревшей — то есть проверка следует за ДЕРЕВОМ, а не за таблицей имён. Отсутствие конфига НЕ считается согласием: возвращается None, а не пустой словарь, и все рычаги числятся нерешёнными; испорченный JSON ведёт себя так же. Отдельно проверено, что причина без числа отвергается — иначе реестр наполнился бы фразами вида «не нужно». Domain: результат осмыслен вне тестов и дважды поправлен замером. Первое: я собирался включить caveman, потому что вывод модели есть главная статья расхода (71.6%). Разбор состава вывода это опроверг — 90.6% суть аргументы инструментов, которые директива исключает по построению, и потолок падает до 6.6%. Второе: я удалил из конфига инертный ключ context_tier как «пустышку», а следующий bootstrap вернул его обратно — и правильно, потому что для проектов, чей файл правил генератор пишет, рычаг живой. Обе поправки записаны в реестре и в тесте, чтобы следующий читатель не повторил ни того, ни другого.
