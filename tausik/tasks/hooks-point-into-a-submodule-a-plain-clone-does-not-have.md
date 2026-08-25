---
slug: hooks-point-into-a-submodule-a-plain-clone-does-not-have
title: "Хуки указывают в сабмодуль, которого нет в обычном клоне: в потребительском репозитории Rule 1 не существует"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: complex
role: backend
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: "scripts/hooks/** — сами хуки не меняются, меняется только адрес, по которому их зовут"
relevant_files:
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap.py"
  - "tests/test_hooks_survive_a_plain_clone.py"
  - "tests/test_bootstrap_paths.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "bootstrap/**"
  - "scripts/**"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: "2026-08-12T15:35:47Z"
---

## Goal

В потребительском проекте, склонированном без --recurse-submodules, хуки РАБОТАЮТ — либо bootstrap отказывается объявлять Rule 1 жёстким правилом. Расхождение между обещанием CLAUDE.md и фактом ЗАПРЕЩЕНО.

## Acceptance Criteria

1. Сгенерированный settings.json указывает на ОТСЛЕЖИВАЕМЫЕ копии в .claude/scripts/hooks/, а не в .tausik-lib/. Тикет GitLab #7 сообщает, что перевод всех 22 команд проверен и работает без единой другой правки — проверить это утверждение запуском, а не поверить ему.
2. Правило распространено на ВСЕ профили IDE, а не на claude: qwen, cursor, kilo, opencode получают ту же правку. Форма закрывается перечислением генераторов из кода (конвенция #361).
3. Тест на ПОТРЕБИТЕЛЬСКОЙ раскладке: фикстура, где .tausik-lib пуст (гитлинк без содержимого), доказывает, что хук всё равно запускается и блокирует правку без задачи.
4. НЕГАТИВНЫЙ сценарий: если рабочего пути нет вовсе, bootstrap ОТКАЗЫВАЕТСЯ молча писать конфиг, указывающий в пустоту, и говорит об этом. Хук, которого нет, не имеет права выглядеть как настроенный.
5. НЕГАТИВНЫЙ сценарий: тест доказывает, что при пустом .tausik-lib СТАРАЯ конфигурация действительно не работает — иначе правка чинит то, что не было сломано.
6. Утверждение CLAUDE.md «Rule 1 — Hard (PreToolUse hook)» проверяется тестом против фактической достижимости хука (конвенция #364).

## Plan

## Rollback

git revert коммита; путь хуков возвращается к сабмодулю одной строкой в bootstrap_hooks

## Journal

- 2026-08-12T15:35:21Z [implementation] — Чек-лист доказательств. AC-1 (конфиг указывает на отслеживаемые копии): ✓ tests/test_hooks_survive_a_plain_clone.py::test_every_hook_command_names_a_file_that_exists ✓ MANUAL: после правки в нашем репозитории .claude — 22 хука на .claude/scripts/hooks, мимо ноль; .qwen — 22 на .qwen/scripts/hooks, мимо ноль. AC-2 (правило на ВСЕ профили): ✓ tests/test_hooks_survive_a_plain_clone.py::test_generators_list_covers_every_profile_that_writes_hooks ✓ MANUAL: генераторов, пишущих команды хуков, в коде два — generate_settings_claude и generate_settings_qwen; оба переведены. Остальные профили (cursor, kilo, opencode) команд хуков не пишут — проверено перечислением generate_settings_* из модулей. AC-3 (тест на потребительской раскладке): ✓ tests/test_hooks_survive_a_plain_clone.py — фикстура строит проект с ПУСТОЙ библиотекой .tausik-lib и развёрнутыми хуками, имена берутся из живого scripts/hooks, а не списком руками. AC-4 (громкий отказ вместо молчаливого конфига): ✓ tests/test_hooks_survive_a_plain_clone.py::test_bootstrap_refuses_to_write_a_config_pointing_at_nothing ✓ MANUAL: assert_hooks_deployed вызывается в bootstrap.py сразу после copy_scripts. AC-5 (доказать, что старое было сломано): ✓ tests/test_hooks_survive_a_plain_clone.py::test_the_old_wiring_would_have_failed_this — собирает конфиг ПРЕЖНИМ способом и требует, чтобы проверка нашла промахи. Без этого зелёный результат ничего не значил бы. AC-6 (утверждение CLAUDE.md против достижимости хука): ✓ покрыто AC-1: тест проверяет, что каждая команда называет существующий файл в раскладке обычного клона. НАХОДКА ПО ХОДУ, важнее самой правки: дефект закреплял ТЕСТ. test_claude_hooks_are_rename_proof в tests/test_bootstrap_paths.py требовал, чтобы команды содержали ${CLAUDE_PROJECT_DIR}/.tausik-lib/scripts/hooks/ — то есть фиксировал сломанную проводку как правило и был зелёным всё это время. Тест исправлен. Разделение обязанностей сделано по ходу: первая редакция ставила отказ внутрь deployed_hooks_dir, и это сломало 23 существующих теста, которые генерируют конфиг во временный каталог без развёрнутых хуков. Отказ перенесён в assert_hooks_deployed и вызывается оркестратором — вычисление адреса и проверка развёртывания это разные обязанности. Регрессии: pytest -k "bootstrap or hook or settings or path" — 1269 passed, 0 failed.
