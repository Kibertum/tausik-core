---
slug: mypy-gate-measures-differently-than-mypy-itself
title: "Гейт mypy меряет не то, что mypy по конфигу проекта: два источника истины о том, ЧТО проверяется"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/gate_registry.py (команда гейта mypy), scripts/gate_command_runner.py (фильтрация по file_extensions/file_patterns без {files}), tests/, CHANGELOG.md, CHANGELOG.ru.md."
scope_exclude: "tests/conftest.py НЕ ПРАВИТСЯ (AC4): три его ошибки — свойство способа вызова, а не типов, и правка файла замаскировала бы настоящий дефект. pyproject.toml [tool.mypy] не трогается: он и есть выбранный единственный источник истины, менять его — значит менять предмет, а не чинить расхождение. Гейт ruff не трогается: у него та же форма `{files}`, но нет расхождения по набору источников — ruff не имеет собственного files=. Гейты со стековыми конфигами не пересматриваются."
relevant_files:
  - "scripts/gate_registry.py"
  - "scripts/gate_command_runner.py"
  - "tests/test_mypy_gate_scope.py"
  - "tests/test_gates.py"
  - "tests/test_gate_registry.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-31T07:56:06Z"
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

НАЙДЕНО В СЕССИИ #191, память #440. Гейт объявлен как `mypy {files}` и подставляет ИЗМЕНЁННЫЕ .py-файлы аргументами. Конфигурация же в pyproject.toml задаёт свой набор источников: files = ["scripts", "harness/claude/mcp/project"], exclude = ["scripts/hooks/"]. Два источника истины о том, ЧТО проверяется, — ровно тот класс дефекта, который этот релиз уже чинил в CLAUDE.md (решение #277: адрес из одного источника, содержимое из другого). ЗАМЕР: `python -m mypy` -> «Success: no issues found in 341 source files», 0.93 s; `python -m mypy tests/conftest.py` -> ТРИ ошибки (import-not-found service_gates:71, import-not-found backend_schema:207, no-any-return:212). Ошибки ложные: файл передан явным аргументом и потому проверяется ВНЕ контекста набора источников, где эти модули резолвятся; в штатном прогоне tests/ не проверяется вовсе. Тот же механизм ударит по scripts/hooks/*.py, которые конфиг исключает намеренно, — mypy не применяет exclude к явно переданным файлам. СЛЕДСТВИЕ, ПЕРЕДАВАВШЕЕСЯ ИЗ СМЕНЫ В СМЕНУ КАК ФАКТ: «mypy на коммит-гейте красный тремя ошибками в tests/conftest.py — дорелизные». Диагноз был неверен: чинить в типах нечего, чинить надо способ вызова. ВТОРАЯ ПОЛОВИНА ДЕФЕКТА, НАЙДЕННАЯ ПРИ РАЗБОРЕ: gate_command_runner применяет file_extensions и file_patterns ТОЛЬКО когда в команде есть подстановка {files} (строки 345 и 358). То есть у гейта без {files} объявление «я про .py» не значит НИЧЕГО и молча игнорируется. Сегодня таких гейтов нет — из трёх командных гейтов (ruff, mypy, bandit) все с {files}, — поэтому исправление ничего не ломает, но без него первый же гейт без подстановки станет запускаться на любой коммит.

## Acceptance Criteria

AC1. Гейт mypy меряет РОВНО то же, что `python -m mypy` по конфигу проекта — источник истины о наборе проверяемых файлов ОДИН, и это pyproject.toml. Проверяется свойством, а не литералом команды: в команде гейта НЕТ подстановки {files} (конвенция #417 запрещает тесты на дословный текст исходника).
AC2. Гейт по-прежнему ОБЛАСТНОЙ: при коммите, не трогающем ни одного .py, он не исполняется, а сообщает «нет подходящих файлов». Для этого gate_command_runner обязан применять file_extensions и file_patterns НЕЗАВИСИМО от наличия {files} в команде.
AC3. НЕГАТИВНЫЙ СЦЕНАРИЙ, ОБЯЗАТЕЛЕН, И ЕГО ДВА. (а) Гейт, НЕ объявивший ни file_extensions, ни file_patterns, обязан исполняться ВСЕГДА — новая фильтрация не имеет права молча выключить его. Пропущенный гейт хуже ложного срабатывания: он выглядит как зелёный. (б) tests/conftest.py, попавший в коммит, БОЛЬШЕ НЕ КРАСИТ гейт. Предъявляется прогоном на настоящем файле: до починки три ошибки, после — чисто.
AC4. Ложные ошибки названы поимённо и показано, что они исчезли ИМЕННО из-за смены способа вызова, а не потому что кто-то поправил типы: tests/conftest.py:71 import-not-found service_gates, :207 import-not-found backend_schema, :212 no-any-return. Сам conftest.py в этой задаче НЕ ПРАВИТСЯ ни одной строкой.
AC5. Мутация обязательна: с возвращённым дефектом (подстановка {files} назад / фильтрация только при наличии {files}) регрессия КРАСНАЯ и называет, что именно разошлось; после возврата побайтовой копией со сверкой sha256 — зелёная. git checkout запрещён.
AC6. После правки scripts/ выполнен `bootstrap --ide all` — иначе правка не доезжает до работающего CLI и MCP (память #438), и гейт продолжит вести себя по-старому, а прогон покажет «починено».
AC7. Цена названа числом, а не словом «дёшево»: замеренная длительность полного прогона mypy приведена в журнале; если она вырастет против прежнего пофайлового вызова, это сказано прямо, а не умолчано.

## Plan

## Rollback

git revert коммита задачи плюс ОБЯЗАТЕЛЬНЫЙ `bootstrap --ide all` после отката — иначе развёрнутые профили останутся с новым поведением, а исходники со старым, и расхождение станет хуже исходного дефекта. Откат возвращает пофайловый вызов и вместе с ним ложные ошибки на tests/conftest.py; гейт объявлен severity=warn, поэтому ни до, ни после откат не блокирует коммит.

## Journal

- 2026-08-31T07:55:22Z [implementation] — [#191] СДЕЛАНО. Правки две, и вторая нашлась только при разборе первой. (1) scripts/gate_registry.py — команда гейта mypy стала `mypy` без подстановки. Источник истины о наборе проверяемых файлов теперь ОДИН: pyproject.toml. (2) scripts/gate_command_runner.py — фильтрация по file_extensions/file_patterns отвязана от наличия {files} в команде. До правки у гейта без подстановки объявление «я про .py» не значило НИЧЕГО и молча игнорировалось. НАХОДКА, КОТОРОЙ НЕ БЫЛО В ЦЕЛИ ЗАДАЧИ И КОТОРАЯ ХУЖЕ ИСХОДНОГО ДИАГНОЗА: ложное срабатывание УСЛОВНО. Замер: `mypy {files}` на ОДНОМ tests/conftest.py — красный (три ошибки); он же на трёх файлах, где рядом лежат scripts/gate_registry.py и scripts/gate_command_runner.py, — ЗЕЛЁНЫЙ, потому что соседний аргумент возвращает mypy путь к пакету и импорты снова резолвятся. То есть вердикт гейта зависел от того, что ещё случайно попало в коммит. Это не проверка типов, а лотерея, и в передачах она читалась как «дорелизный долг» — устойчивое утверждение о состоянии кода там, где было свойство способа вызова. AC7, ЦЕНА ЗАМЕРОМ, А НЕ СЛОВОМ: прежняя форма, один изменённый файл 0.19 s прежняя форма, три файла 0.42 s НОВАЯ форма, проект целиком 0.46 s НОВАЯ форма, коммит без .py 0.00 s (гейт пропущен по области) Рост есть и он назван: до +0.27 s против пофайловой формы в лучшем для неё случае. Взамен новая форма ловит СТРОГО БОЛЬШЕ — правка в одном модуле, ломающая типы в другом, пофайловому прогону не видна вовсе. ДВА СУЩЕСТВУЮЩИХ ХРАПОВИКА ПОКРАСНЕЛИ, И ОБА РАЗОБРАНЫ, А НЕ СНЯТЫ. tests/test_gates.py::test_no_placeholder_filter_not_applied закреплял РОВНО то поведение, которое опознано дефектом («если в команде нет {files}, фильтр не применять»). Тест ПЕРЕВЁРНУТ, переименован в test_no_placeholder_still_honours_the_declared_scope, и его докстринг называет прежний контракт поимённо — чтобы следующий читатель не решил, что защита потеряна случайно. Настоящая защита, которую он нёс (гейт без объявленной области не имеет права быть пропущенным), сохранена в двух тестах: test_no_extensions_config_behaves_as_before и новый test_gate_without_scope_declaration_always_runs. От старого поведения не зависело НИЧТО: все три командных гейта (ruff, mypy, bandit) подставляют {files}, ветка была недостижима в эксплуатации, и наблюдал её только тот тест. tests/test_gate_registry.py::test_universal_gates_unchanged_by_the_refactor — снимок конфигов, замороженный вручную. Обновлена ОДНА запись (command и description гейта mypy) с комментарием, называющим причину; enabled, severity, trigger и file_extensions остались закреплены и продолжают ловить дрейф. МУТАЦИЯ (AC5), ДВЕ, ПО ОДНОЙ НА КАЖДЫЙ ИЗМЕНЁННЫЙ ФАЙЛ. A. Возвращено условие `and "{files}" in cmd`. sha ДО 09839446e18c30cb. Прогон: 2 failed / 13 passed — упали test_extension_scope_applies_without_files_placeholder и test_no_placeholder_still_honours_the_declared_scope, то есть ровно те, что отвечают за свойство. Возврат побайтовой копией: sha совпал. B. Возвращена подстановка `mypy {files}`. sha ДО 9e57ecb644dcfeee. Прогон: 3 failed / 31 passed — упали test_mypy_gate_does_not_interpolate_files, test_conftest_no_longer_reddens_the_mypy_gate и снимок реестра. Возврат побайтовой копией: sha совпал. git checkout не применялся ни разу — дерево грязное. Итоговый зелёный: 162 passed по четырём файлам гейтов. AC6: `python bootstrap/bootstrap.py --ide all` выполнен, exit 0. Проверено, что развёрнутый профиль несёт обе правки: .claude/scripts/gate_registry.py содержит `"command": "mypy",`, .claude/scripts/gate_command_runner.py содержит `if file_exts_raw:`. Живой `tausik gates status` в свежем процессе печатает `cmd: mypy` и новое описание. ВАЖНО ДЛЯ СЛЕДУЮЩЕЙ СМЕНЫ: сервер MCP этой сессии запущен ДО развёртывания и держит прежний реестр в памяти — третье звено цепи (правка -> bootstrap -> перезапуск сервера) по-прежнему не выражено нигде, задача bootstrap-drift-gate-off-source-edits-never-reach-the-cli. AC4: tests/conftest.py не тронут ни одной строкой — закреплено тестом test_conftest_itself_was_not_edited.
- 2026-08-31T07:56:05Z [implementation] — AC-1: ✓ tests/test_mypy_gate_scope.py::test_mypy_gate_does_not_interpolate_files — проверяется СВОЙСТВО (нет подстановки), а не литерал команды, по конвенции #417. AC-2: ✓ tests/test_mypy_gate_scope.py::test_extension_scope_applies_without_files_placeholder AC-2: ✓ tests/test_mypy_gate_scope.py::test_extension_scope_lets_python_through AC-2: ✓ tests/test_gates.py::TestCommandGateFileExtensions::test_no_placeholder_still_honours_the_declared_scope AC-3: ✓ tests/test_mypy_gate_scope.py::test_gate_without_scope_declaration_always_runs — негативный (а): гейт без объявленной области исполняется ВСЕГДА, пропущенный гейт выглядит как зелёный и потому хуже ложного срабатывания. AC-3: ✓ tests/test_mypy_gate_scope.py::test_empty_extension_list_is_not_a_scope_declaration AC-3: ✓ tests/test_mypy_gate_scope.py::test_conftest_no_longer_reddens_the_mypy_gate — негативный (б) на НАСТОЯЩЕМ файле. AC-4: ✓ tests/test_mypy_gate_scope.py::test_the_old_form_is_what_reddened_it — доказывает ПРИЧИНУ: прежняя форма на том же файле красная и красная именно import-not-found. AC-4: ✓ tests/test_mypy_gate_scope.py::test_conftest_itself_was_not_edited AC-5: ✓ мутация вручную, две. A: возвращено 'and {files} in cmd', sha ДО 09839446e18c30cb -> 2 failed / 13 passed (упали ровно те два теста) -> возврат побайтовой копией, sha совпал. B: возвращена подстановка 'mypy {files}', sha ДО 9e57ecb644dcfeee -> 3 failed / 31 passed -> возврат, sha совпал. git checkout не применялся. AC-6: ✓ python bootstrap/bootstrap.py --ide all, exit 0; развёрнутый профиль несёт обе правки; живой gates status в свежем процессе печатает 'cmd: mypy'. AC-7: ✓ цена замерена: прежняя форма 0.19 s (один файл) и 0.42 s (три файла), новая 0.46 s (проект целиком), 0.00 s на коммите без .py. Рост назван прямо: до +0.27 s. Зелёный прогон: verification_run #1859, exit=0, ruff PASS, pytest PASS (24 из 413 файлов, 15.06 s). Domain: результат осмыслен вне тестов. Гейт теперь меряет ровно то, что меряет 'python -m mypy' по конфигу проекта — 341 файл, ноль ошибок, — и ловит СТРОГО БОЛЬШЕ прежнего: правка в одном модуле, ломающая типы в другом, пофайловому прогону невидима вовсе. Сверх исходного диагноза замером вскрыто, что прежнее ложное срабатывание было УСЛОВНЫМ: tests/conftest.py в одиночку красный, он же рядом со scripts/*.py зелёный, потому что соседний аргумент возвращает mypy путь к пакету. Вердикт, зависящий от того, что ещё попало в коммит, — не проверка типов; это и было главной ценой дефекта.
- 2026-09-26T19:02:56Z [done] — EVIDENCE-MOVED: tests/test_gates.py::test_no_placeholder_filter_not_applied => tests/test_gates.py::test_no_placeholder_still_honours_the_declared_scope
