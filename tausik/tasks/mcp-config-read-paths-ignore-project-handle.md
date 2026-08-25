---
slug: mcp-config-read-paths-ignore-project-handle
title: "Читающие пути конфига в MCP резолвят проект от cwd, а не от svc: gates_status опишет чужой проект"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: mcp-gate-toggle-mutates-real-project-config
scope: "scripts/project_config.py (load_config/load_config_with_rejections/load_gates/get_gates_for_trigger — параметр tausik_dir), scripts/project_service.py (gates_status → self.tausik_dir()), harness/claude/mcp/project/handlers.py (_handle_gates_status(svc), _handle_status), tests/ (негативный + позитивный тесты изоляции)"
scope_exclude: "Не параметризовать user/managed тиры config_trust (они НЕ проектные — иначе новый дефект вместо старого). Не менять read-path enforce_verify_first (отдельная задача при необходимости). Не менять текстовый формат вывода gates status. Не трогать пути ЗАПИСИ (уже исправлены в #125)."
relevant_files:
  - "scripts/project_config.py"
  - "scripts/project_service.py"
  - "harness/claude/mcp/project/handlers.py"
  - "tests/test_config_read_project_scope.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-20T23:12:54Z"
---

## Goal

ОСТАТОК ОТ mcp-gate-toggle-mutates-real-project-config (сессия #125), вынесен ОСОЗНАННО, а не забыт. Там чинился путь ЗАПИСИ; ровно тот же дефект остался на путях ЧТЕНИЯ и не тянулся в ту задачу потому, что чтение не разрушает состояние и не уничтожает свидетельство о себе — это другой вес, а не другая природа.

ГДЕ. (1) harness/claude/mcp/project/handlers.py:_handle_gates_status — зовёт load_gates()/load_config() без каталога. (2) scripts/project_service.py:ProjectService.gates_status — метод ЭКЗЕМПЛЯРА, но конфиг берёт от cwd, то есть игнорирует собственный self ровно как это делал @staticmethod gate_enable до правки. (3) handlers.py:964 — чтение DEFAULT_SESSION_MAX_MINUTES/load_config тем же способом.

ЧЕМ ПЛОХО ИМЕННО ЧТЕНИЕ. Ответ отдаётся как свойство ЗАПРОШЕННОГО проекта, а описывает тот, в котором стоит процесс. Сегодня это совпадает и потому невидимо: MCP-сервер стартует с cwd в корне проекта. Совпадение перестаёт держаться ровно на эпике v2-global-mcp (gmcp-project-resolver, gmcp-server-multitenant), где svc и станет носителем идентичности проекта, — и тогда `gates status` покажет состав гейтов ЧУЖОГО проекта, не соврав ни в одном слове.

ПОЧЕМУ НЕ ОТЛОЖИТЬ ДО ТОГО ЭПИКА. К моменту переезда эти вызовы будут выглядеть работающими, и искать их придётся по симптому «цифры не те», а не по отказу. Дешевле привязать чтение к проекту сейчас, пока известно, где оно.

ЧТО СДЕЛАТЬ. Протянуть tausik_dir через load_config/load_config_with_rejections/load_gates по образцу уже сделанного в #125 для load_project_config/save_config/get_config_path, и заставить gates_status пользоваться self.tausik_dir(). ВНИМАНИЕ К config_trust.resolve: user/managed тиры — НЕ проектные, они читаются из ~/.tausik и $TAUSIK_MANAGED_CONFIG и от каталога проекта зависеть НЕ ДОЛЖНЫ; параметризовать надо ТОЛЬКО проектный тир, иначе получим новый дефект вместо старого.

НЕГАТИВНЫЙ, ОБЯЗАТЕЛЬНЫЙ К ПРОВЕРКЕ: вызов без tausik_dir обязан вести себя побайтово как сейчас (весь CLI ходит именно так), иначе правка тихо переопределит поведение CLI ради MCP.

ГЕЙТ СУЩЕСТВУЕТ ЧАСТИЧНО: autouse-фикстура tests/conftest.py::_guard_live_project_config (добавлена в #125) ловит ЗАПИСЬ в живой конфиг, но ЧТЕНИЕ чужого конфига она поймать не может по устройству. Нужен тест, дающий svc на tmp_path конфиг с заведомо ОТЛИЧНЫМ составом гейтов и требующий, чтобы gates_status вернул ЕГО, а не проектный.

## Acceptance Criteria

AC1. load_config / load_config_with_rejections / load_gates принимают tausik_dir (default None); только ПРОЕКТНЫЙ тир параметризуется (через load_project_config). config_trust.resolve и user/managed тиры (~/.tausik, $TAUSIK_MANAGED_CONFIG) от каталога проекта НЕ зависят — не трогаются.
AC2. ProjectService.gates_status использует self.tausik_dir() для load_gates/load_config.
AC3. handlers._handle_gates_status(svc) и _handle_status передают каталог из svc; регистрационная лямбда tausik_gates_status пробрасывает svc.
AC4. Обратная совместимость CLI: вызов load_config()/load_gates() без tausik_dir даёт побайтово тот же результат, что до правки — доказано тестом.
AC5. Изоляция: svc с конфигом на tmp_path, где состав/enabled гейтов иной, — gates_status возвращает состав ИЗ ЭТОГО каталога, а не из cwd-проекта. Доказано тестом.
AC6. Регресс: полный suite зелёный; autouse _guard_live_project_config не срабатывает.
AC7. Край (негативный): gates_status при пустом или отсутствующем config.json в объявленном каталоге возвращает дефолтные гейты и не падает с exception.

## Plan

## Rollback

git revert коммита. Правка чисто аддитивна — новые опциональные параметры tausik_dir=None с сохранением прежнего поведения при None; откат не затрагивает схему БД и конфиг-файлы.

## Journal

- 2026-07-20T23:11:27Z [implementation] — Реализовано: tausik_dir проброшен через load_config/load_config_with_rejections/load_gates/get_gates_for_trigger (только ПРОЕКТНЫЙ тир — через load_project_config; config_trust user/managed тиры не трогались). gates_status использует self.tausik_dir(). handlers._handle_gates_status(svc) + регистрационная лямбда пробрасывает svc; _handle_status читает session_max от svc.tausik_dir(). 6 тестов (test_config_read_project_scope.py): изоляция gates_status по каталогу, обратная совместимость ambient-чтения, независимость user-тира от каталога проекта, край пустого конфига, handler. Полный suite 5162 passed (после регенерации doc-constants). bootstrap --ide all прогнан.
- 2026-07-20T23:12:34Z [implementation] — AC verified: AC1 ✓ tausik_dir только на проектный тир, config_trust user/managed не трогались — test_user_tier_is_project_dir_independent (user-тир применяется независимо от каталога проекта). AC2 ✓ gates_status→self.tausik_dir() — test_gates_status_describes_its_own_project. AC3 ✓ handler+лямбда — test_handle_gates_status_renders_svc_project. AC4 ✓ обратная совместимость: ambient-чтение игнорирует чужой каталог — test_declared_dir_read_uses_it_and_ambient_ignores_it. AC5 ✓ изоляция gates_status по каталогу (active_stacks marker + mypy override). AC6 ✓ полный suite 5162 passed, _guard_live_project_config не сработал. AC7 ✓ край пустого конфига → дефолты без exception — test_gates_status_empty_config_returns_defaults. Domain: gates status теперь описывает ЗАПРОШЕННЫЙ проект, а не cwd — доказано на живом verify #1116; критично для v2-global-mcp где svc станет носителем идентичности.
- 2026-07-20T23:12:47Z [implementation] — Root cause (integration-mismatch): читающие пути конфига (load_config/load_gates/gates_status/_handle_gates_status/_handle_status) резолвили .tausik от cwd процесса, а не от идентичности проекта в svc — тот же дефект cwd-резолвинга, что был на путях ЗАПИСИ (mcp-gate-toggle #125), но чтение не разрушает состояние, поэтому вынесено отдельно. Невидим пока cwd MCP-сервера = корень проекта; ломается на v2-global-mcp где svc станет носителем проекта. Prevention: экземплярные методы обязаны читать состояние проекта через self.tausik_dir(), а функции конфига — принимать tausik_dir; добавлен позитивный тест изоляции (config на tmp_path с иным составом → gates_status обязан вернуть ЕГО).
- 2026-07-20T23:12:53Z [implementation] — AC1-7 verified (см. предыдущий лог + root cause). Полный suite 5162 passed, verify #1116 PASS.
