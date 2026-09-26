---
slug: write-gate-resolves-a-script-path-against-the-wrong-directory
title: "Путь скрипта резолвится от каталога проекта: четвёртое место того же отождествления, пропущенное инвентарём по имени переменной"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: write-gate-resolves-relative-paths-against-the-wrong-directory
scope: null
scope_exclude: "Не трогаем _OPEN_RE и его подмену на ast — это отдельная открытая задача write-gate-reads-open-literals-out-of-strings-and-comments. Предмет здесь — ТОЛЬКО каталог, от которого резолвится путь скрипта."
relevant_files:
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/shell_channel.py"
  - "scripts/hooks/bash_write_gate.py"
  - "tests/test_write_gate_resolves_against_shell_cwd.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/shell_channel.py"
  - "scripts/hooks/bash_write_gate.py"
  - "tests/**"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-01T17:00:35Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО В #205 СРАЗУ ПОСЛЕ ЗАКРЫТИЯ write-gate-resolves-relative-paths-against-the-wrong-directory, ЧЕТВЁРТОЕ МЕСТО ТОГО ЖЕ ОТОЖДЕСТВЛЕНИЯ.

ЧТО ИМЕННО. scripts/hooks/bash_write_parse.py, функция _script_file_writes: project_dir берётся из CLAUDE_PROJECT_DIR, затем path = script если он абсолютный, иначе os.path.join(project_dir, script). То есть путь СКРИПТА в команде «python helper.py» резолвится от каталога проекта, а не от каталога оболочки — ровно то отождествление, что уже снято в bash_write_gate, memory_pretool_block и task_gate.

ПОЧЕМУ ПРОПУЩЕНО. Инвентарь той задачи снимался grep по join(project_dir, expanded) и join(project_dir, path). Здесь переменная называется script, и совпадения не было. Признак искали по ИМЕНИ ПЕРЕМЕННОЙ, а надо было по ВЫЗОВУ join(project_dir с любым вторым доводом.

СЛЕДСТВИЕ, КОТОРОЕ НАДО ИЗМЕРИТЬ, А НЕ ОБЪЯВИТЬ. Работая во второй выгрузке, гейт прочитает ОДНОИМЁННЫЙ файл из главного дерева либо не найдёт файла вовсе. Первое опаснее: цели записи будут взяты из ЧУЖОГО содержимого — и фантом, и пропуск сразу. НАЧАТЬ С ЗАМЕРА: два дерева, одноимённый helper.py с разным содержимым, показать, чьи цели вернул разбор.

ИНВЕНТАРЬ ЗАНОВО И ПО ВЫЗОВУ, А НЕ ПО ИМЕНИ. Проверить ВСЕ вхождения join(project_dir и os.getcwd() в scripts/hooks, и для каждого сказать, резолвит ли оно путь, приходящий ИЗВНЕ (из команды или payload). Число четыре есть ИЗМЕРЕННОЕ на сегодня, а не граница.

## Acceptance Criteria

1. ЗАМЕР ДО ПОЧИНКИ, ФАКТОМ. Два дерева с ОДНОИМЁННЫМ helper.py разного содержания; предъявлено, чьи цели вернул разбор, когда оболочка стоит в чужой выгрузке. Сказано, что именно происходит: читается чужой файл, не читается ничего, или читается верный.
2. ИНВЕНТАРЬ ЗАНОВО ПО ВЫЗОВУ, А НЕ ПО ИМЕНИ ПЕРЕМЕННОЙ. Проверены ВСЕ вхождения join(project_dir и os.getcwd() в scripts/hooks; для каждого сказано, резолвит ли оно путь, пришедший ИЗВНЕ (из команды или payload), и попадает ли в починку. Предъявлено ЧИСЛО найденных мест — измеренное, а не унаследованное из заголовка.
3. ПОЧИНЕНО ТЕМ ЖЕ ПОМОЩНИКОМ _common.shell_cwd, что и три предыдущих места, а не второй копией правила.
4. НЕ ПРЕВРАЩЕНО В ПОД-ОБНАРУЖЕНИЕ: скрипт, который ДЕЙСТВИТЕЛЬНО лежит в проекте, по-прежнему читается и его цели по-прежнему судятся ACL. Проверено тестом.
5. ПАДЕНИЕ В СТОРОНУ ПРЕЖНЕГО ПОВЕДЕНИЯ: без поля cwd резолв остаётся от project_dir. Проверено тестом.
6. МУТАЦИИ: каждая правка проверена мутацией на свой предмет, ни одна не ДОБАВЛЯЕТ проверку (память #503). Число предъявлено.
7. Полная лента зелёная, mypy чисто, doctor All clean.

## Plan

## Rollback

git revert коммита задачи; резолв пути скрипта возвращается к каталогу проекта.

## Journal

- 2026-09-01T16:59:20Z [implementation] — AC-1: ✓ manual: замер на двух деревьях с одноимённым helper.py разного содержания. Стоя в чужой выгрузке, разбор вернул PROJECT_TARGET.txt — цель ГЛАВНОГО дерева. После удаления скрипта из чужого дерева ответ НЕ ИЗМЕНИЛСЯ: те же цели по файлу, которого команда не запускает. То есть фантом и пропуск одновременно. AC-2: ✓ manual: инвентарь пересnят ПО ВЫЗОВУ, а не по имени переменной. join(project_dir встречается в scripts/hooks 36 раз; 35 приклеивают КОНСТАНТНЫЙ внутренний путь (.tausik/tausik.db, .claude/skills, .tausik/venv и подобные) и потому верны. РОВНО ОДНО приклеивало путь, пришедший извне, — bash_write_parse.py:107. Четвёртое место есть ИЗМЕРЕННОЕ, а не унаследованное из заголовка. AC-3: ✓ scripts/hooks/bash_write_parse.py: базовый каталог протянут доводом от события через shell_channel; отдельной копии правила не заведено. В pwsh-диалект НЕ передаётся сознательно — он не открывает скриптов. AC-4: ✓ tests/test_write_gate_resolves_against_shell_cwd.py::TestTheScriptPathResolvesThere::test_the_same_script_at_home_is_still_judged AC-5: ✓ tests/test_write_gate_resolves_against_shell_cwd.py::TestTheScriptPathResolvesThere::test_without_a_base_directory_it_still_reads_the_project AC-6: ✓ manual: мутаций 4, убито 4, ни одна не добавляет проверку. M2 и M3 (снятие протяжки в shell_channel и в гейте) СПЕРВА ВЫЖИЛИ: мой сквозной тест не различал два прочтения, потому что при относительной цели ОБА ответа оказывались вне дерева. Тест переписан на АБСОЛЮТНУЮ внутрипроектную цель, которая эти прочтения разделяет, — после чего обе мутации убиты. AC-7: ✓ manual: см. прогон полной ленты, mypy Success: no issues found in 331 source files, doctor All clean. Negative: ✓ tests/test_write_gate_resolves_against_shell_cwd.py::TestTheScriptPathResolvesThere::test_the_same_script_at_home_is_still_judged — дома скрипт по-прежнему читается и его цели по-прежнему судятся ACL. Negative: ✓ tests/test_write_gate_resolves_against_shell_cwd.py::TestTheScriptPathResolvesThere::test_without_a_base_directory_it_still_reads_the_project — без базового каталога поведение прежнее, то есть починка не может тихо перестать судить. Root cause (logic-error): путь СКРИПТА, названный командой, резолвился от project_dir, как и три уже исправленных места, поэтому во второй выгрузке читался одноимённый файл главного дерева. Место пропущено инвентарём, который искал признак ПО ИМЕНИ ПЕРЕМЕННОЙ (expanded, path), а не по вызову. Prevention: инвентарь снимать по ВЫЗОВУ и по роли довода (пришёл ли путь извне), а не по написанию; и различать в перечне константные внутренние пути от внешних — их 35 против 1, и смешение прячет единственный значимый случай.
- 2026-09-01T17:01:03Z [done] — Domain: осмысленность вне тестов держится на факте файловой системы, а не на модели. helper.py в git worktree и одноимённый helper.py в главном дереве суть РАЗНЫЕ файлы с разным содержимым; команда python helper.py запускает тот, который лежит там, где стоит оболочка. Гейт читал другой — то есть делал утверждения о записях по содержимому файла, который не исполняется. Это проверяемо вне наших тестов: два дерева, одноимённый скрипт, и ответ разбора сверяется с тем, что реально запустит bash. ОЦЕНКА СЛОЖНОСТИ ЗАНИЖЕНА, ЗАПИСЫВАЮ ЧЕСТНО. Объявил simple, гейт при закрытии посчитал medium: правка тронула 4 несущих файла из 6 объявленных. Занижение НЕ безобидно — жёсткие гейты QG-0 по объёму и откату ключуются на сложность, поэтому SENAR Rule 2 и Rule 6 были понижены до предупреждений. Я оценил по РАЗМЕРУ ПРАВКИ (одна строка резолва), а надо было по ЧИСЛУ МЕСТ, которые придётся тронуть, чтобы эту строку получить: протяжка довода прошла через разбор, диспетчер диалектов и сам гейт.
