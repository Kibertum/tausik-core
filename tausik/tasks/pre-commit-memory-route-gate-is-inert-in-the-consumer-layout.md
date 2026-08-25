---
slug: pre-commit-memory-route-gate-is-inert-in-the-consumer-layout
title: "Гейт memory-route в pre-commit не находит себя у потребителя и молча не запускается"
status: done
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: "bootstrap/** — вопрос в хуке и его разрешении, не в развёртывании"
relevant_files:
  - "scripts/hooks/pre-commit"
  - "tests/consumer_layout.py"
  - "tests/test_consumer_layout.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/**"
  - "tests/*.py"
  - "docs/**"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-12T19:42:22Z"
---

## Goal

Защитный гейт либо запускается, либо говорит, что не смог. Молчаливая инертность защите не годится.

## Acceptance Criteria

1. Воспроизведение ДО правки: scripts/hooks/pre-commit:15-18 ищет гейт по двум адресам — scripts/gate_memory_route.py и .tausik-lib/scripts/gate_memory_route.py. У потребителя scripts/ принадлежит ПРОЕКТУ, а .tausik-lib при клоне без --recurse-submodules пуст; развёрнутая копия .claude/scripts/gate_memory_route.py не пробуется вовсе. MEMORY_ROUTE_GATE остаётся пустым, блок пропускается, гейт не выполняется.
2. Гейт находится в потребительской раскладке: адрес разрешается тем же правилом, к которому сведён остальной класс, — развёрнутый профиль, затем библиотека, затем проект. Профили спрашиваются у ide_utils.all_profile_dirs(), а не перечисляются руками.
3. НЕ НАЙДЕН — значит СКАЗАНО. Если гейта нет ни по одному адресу, хук печатает это в stderr. Сейчас комментарий на строке 14 объявляет молчаливую инертность допустимой («Inert when scripts/ is absent»); для защитного контроля она недопустима, потому что docs/en/security.md:144 обещает применение deny-list'а «IDE-agnostically over the working tree».
4. НЕГАТИВНЫЙ: явно выключенный гейт (gates.memory_route.enabled=false) по-прежнему не блокирует коммит и не шумит. Отличать «выключен» от «не найден» обязательно.
5. НЕГАТИВНЫЙ: правка не заставляет хук падать в репозитории разработки, где project_dir == lib_dir и гейт лежит в scripts/.
6. Регрессия закреплена тестом на фикстуре tests/consumer_layout.py: MEMORY_ROUTE_GATE разрешается в существующий файл при empty_lib=True.

## Plan

## Rollback

git revert

## Journal

- 2026-08-12T19:23:31Z [implementation] — Правка вскрыла ЧЕТЫРЕ копии одной догадки в одном файле, а не одну. (1) Адрес гейта: искался в scripts/ и .tausik-lib/scripts/, развёрнутый профиль не пробовался. (2) Адрес RAG-сервера: пробовался только .claude из семи профилей. Обе сведены к find_engine_file; профили ищутся глобом .[!.]*, а не списком — список назвал бы .claude и пропустил остальные, а спросить ide_utils.all_profile_dirs() из shell-скрипта, ещё не нашедшего движок, неоткуда. Глоб именно .[!.]*, потому что .* раскрывается и в '..' и увёл бы поиск в РОДИТЕЛЬСКИЙ каталог. (3) Интерпретатор Python: цепочка [ -f ] заканчивалась голым python, которого в Git Bash под Windows в PATH нет. Проверка «файл существует» на имя команды не отвечает вообще, а на путь отвечает не на тот вопрос: C:/Python311/python.exe существует и не запускается — MSYS ждёт /c/Python311/python.exe. Кандидат теперь ЗАПУСКАЕТСЯ. (4) mypy звался голым python — четвёртая копия. Дважды красный тест был не дефектом кода, а способом запуска: bash -c теряет позиционные параметры функции (git запускает хук ФАЙЛОМ, проверка теперь тоже), а heredoc внутри $( ) под Git Bash отдавал пустой ответ молча.
- 2026-08-12T19:42:20Z [implementation] — AC-1 (воспроизведение ДО правки): ✓ MANUAL: чтением кода подтверждено — хук искал два адреса, оба недостижимых у потребителя, развёрнутый профиль не пробовался; переменная оставалась пустой и блок пропускался. Найдено адверсариальным ревью, проверено лично. AC-2 (гейт находится в потребительской раскладке общим правилом, профили из глоба): ✓ tests/test_consumer_layout.py::test_the_memory_route_gate_is_reachable_in_a_plain_clone — проверка гоняет ЖИВУЮ функцию find_engine_file, вырезанную из самого файла хука, а не переписанную копию правила. ✓ ::test_the_search_does_not_step_into_the_parent_directory — глоб .[!.]*, потому что .* раскрывается в '..' и поиск ушёл бы в родительский каталог; приманка рядом с проектом не подбирается. ✓ ::test_the_engines_own_repo_prefers_its_source_over_the_deployed_copy — в репозитории движка побеждает исходник, иначе коммит проверялся бы вчерашней копией. AC-3 (НЕ НАЙДЕН — значит СКАЗАНО): ✓ ::test_a_gate_that_cannot_find_itself_says_so — предупреждение в stderr, код возврата 0. Предупреждение, а не блокировка: блокировка выдумала бы новый отказ для проектов, у которых движка никогда не было. AC-4 (НЕГАТИВНЫЙ: выключенный решением гейт не шумит и не блокирует): ✓ ::test_a_gate_switched_off_by_decision_stays_quiet. AC-5 (НЕГАТИВНЫЙ: в репозитории разработки хук не падает): ✓ ::test_the_engines_own_repo_prefers_its_source_over_the_deployed_copy ✓ MANUAL: bash -n scripts/hooks/pre-commit — синтаксис чист. AC-6 (регрессия на фикстуре consumer_layout): ✓ фикстура дополнена развёрнутым gate_memory_route.py, потому что copy_scripts разворачивает весь scripts/, а не одни хуки. Обнаружено СВЕРХ критериев и исправлено: в файле было ЧЕТЫРЕ копии одной догадки — адрес гейта, адрес RAG-сервера (пробовался только .claude из семи профилей), разрешение интерпретатора и вызов mypy голым python. Интерпретатор теперь ЗАПУСКАЕТСЯ, а не проверяется на [ -f ]: C:/Python311/python.exe существует и не запускается, MSYS ждёт /c/... . Добавлено переопределение TAUSIK_PYTHON и кандидаты python3/py. Domain: сквозные проверки исполняют настоящий bash над настоящим текстом хука в настоящем дереве; два ложных красных были свойством СПОСОБА ЗАПУСКА (bash -c теряет $1 функции; heredoc в $() под Git Bash отдаёт пустоту) и записаны в память #395, а не обойдены. Полный прогон: 7001 passed, 24 skipped, 0 failed. Собственный храповик test_hook_encoding поймал мои же два subprocess без encoding — исправлено. ruff чист.
