---
slug: scaffold-opencode-output-mode-opencode
title: "Дефект фикса: scaffold_opencode принимает output_mode, но диспетчер его не передаёт — OpenCode молча без режима"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: critical-output-mode-no-op-bootstrap-caveman
scope: "bootstrap/bootstrap.py (передача параметра), tests/test_caveman_wiring_integration.py (параметризация по SCAFFOLD_IDES)"
scope_exclude: "Не менять сигнатуры генераторов и резолвер — они корректны. Не трогать caveman-директиву. Не рефакторить диспетчер заодно."
relevant_files:
  - "bootstrap/bootstrap.py"
  - "tests/test_caveman_wiring_integration.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-16T20:35:08Z"
---

## Goal

Найдено при само-проверке перед отгрузкой 1.7.0 (пользователь усомнился и попросил ещё ревью — оказался прав). bootstrap.py:202-204 зовёт scaffold_opencode(project_dir, target_dir, venv_python, lib_dir, config, stacks, context_tier) — БЕЗ output_mode, хотя сигнатура (bootstrap_opencode.py:295-304) его принимает восьмым параметром с дефолтом "off". Итог: из пяти IDE OpenCode ЕДИНСТВЕННЫЙ не получает caveman-режим даже после фикса корневой проводки. Воспроизведено: временный проект с корневым output_mode=caveman → bootstrap_ide(ide='opencode') → .opencode/tausik-rules.md БЕЗ директивы (ожидалось True, получено False). Тот же класс тихого no-op, который эта же цепочка задач и чинила. ПРИЧИНА, ПОЧЕМУ ПРОСПАЛИ: мой integration-тест (test_caveman_wiring_integration.py) гонял только claude/agents — параметризации по всем IDE не было, поэтому дефект в opencode-ветке был невидим.

## Acceptance Criteria

1. bootstrap.py передаёт output_mode в scaffold_opencode. 2. НЕГАТИВНЫЙ СЦЕНАРИЙ (обязателен): integration-тест параметризован по ВСЕМ scaffold-IDE (claude, cursor, qwen, opencode) и проверяет, что корневой output_mode=caveman доезжает до файла правил КАЖДОЙ. ОШИБКА, если тест зелёный на текущем сломанном коде — обязан краснеть на opencode ДО фикса (проверить экспериментом: убрать передачу → красный → вернуть → зелёный). 3. ОШИБКА, если параметризация берётся из хардкод-списка вместо SCAFFOLD_IDES: новая IDE обязана автоматически попадать под гард, иначе следующая проводка снова окажется непокрытой. Учесть, что у cursor файл .cursorrules, у qwen QWEN.md, у opencode .opencode/tausik-rules.md — резолвить путь правил через реестр/маппинг, а не наугад. 4. ОШИБКА, если какая-либо ДРУГАЯ ветка диспетчера теряет параметр так же — проверить kilo (у него генератора правил нет — зафиксировать это явно, чтобы не выглядело пропуском). 5. Обе полосы зелёные (-m '' И дефолт), doctor чист, gates зелёные.

## Plan

## Rollback

git revert; правка в одну строку + тест.

## Journal

- 2026-07-16T20:35:08Z [implementation] — AC verified на ТИХОМ дереве (без параллельных агентов): FULL (pytest -m "") 4716 passed, 21 skipped, 0 failed; FAST 4583 passed; doctor All clean; gates зелёные. Integrity-recheck ПОСЛЕ прогона: resolve_output_mode(full_cfg)=1 — дерево не поехало во время прогона. 1. ✓ bootstrap.py:202-205 передаёт output_mode в scaffold_opencode. До фикса вызов шёл без него, параметр падал в дефолт "off" → из 5 IDE OpenCode ЕДИНСТВЕННЫЙ не получал режим. Воспроизведено до фикса: временный проект с корневым output_mode=caveman → .opencode/tausik-rules.md БЕЗ директивы. 2. ✓ НЕГАТИВНЫЙ СЦЕНАРИЙ ДОКАЗАН: tests/test_caveman_wiring_integration.py::TestEveryScaffoldIdeGetsTheMode параметризован и гоняет НАСТОЯЩИЙ bootstrap_ide для claude/cursor/qwen/opencode. Проверено на красноту: убрал передачу output_mode → FAILED именно на [opencode], 1 failed; вернул → 17 passed. Гард ловит ровно тот дефект, ради которого написан. 3. ✓ Параметризация НЕ из хардкода: test_rules_file_map_covers_every_scaffold_ide сверяет _RULES_FILE со SCAFFOLD_IDES из кода — новая IDE обязана быть объявлена, иначе тест краснеет, а не тихо тестирует 4 из 6. Пути правил замаплены по факту (claude→CLAUDE.md, cursor→.cursorrules, qwen→QWEN.md, opencode→.opencode/tausik-rules.md), не угаданы. 4. ✓ Прочие ветки проверены: kilo НЕ имеет генератора правил (читает AGENTS.md, который пишется отдельно) — зафиксировано тестом test_kilo_has_no_rules_generator_by_design, чтобы отсутствие не выглядело пропуском. claude/cursor/qwen получают output_mode позиционным аргументом — покрыты параметризацией. 5. ✓ Обе полосы зелёные, doctor чист, filesize зелёный (395 строк). ИНЦИДЕНТ С «ОТКАТОМ» ФАЙЛА — ПРИЧИНА УСТАНОВЛЕНА, ЭТО НЕ МИСТИКА: bootstrap.py многократно откатывался (в т.ч. до состояния HEAD/v1.6.1, теряя ВСЮ ветку OpenCode) — это делали МОИ ЖЕ ревью-агенты. В задании я написал им «RUN things», «reproduce», «construct the exact broken input», а у tausik-reviewer есть Bash: они воспроизводили баги ПРЯМО В ЖИВОМ ДЕРЕВЕ и возвращали назад; один не успел вернуть. Отсюда скачки размера файла (13935↔13522), мигающий git status и падение моей же integrity-проверки, которое я едва не списал на ложную тревогу — а она была права В ТОТ МОМЕНТ. Остановил обе фоновые задачи, восстановил из бэкапа (оба бэкапа целы, идентичны, 395 строк), проверил на тихом дереве: 20/20 заявлений CHANGELOG подтверждены кодом. ВЫВОД ДЛЯ ПРОЦЕССА: ревью-агентам с Bash нельзя давать живое рабочее дерево, если сам в нём работаешь — только isolation:"worktree". Предыдущие «зелёные» прогоны шли ОДНОВРЕМЕННО с ревью, т.е. их цвет был недостоверен; этот — первый достоверный. Domain: вне тестов пользователь с корневым output_mode=caveman теперь получает директиву во ВСЕХ пяти хостах, включая OpenCode; раньше OpenCode молча оставался без режима, а bootstrap рапортовал успех.
- 2026-07-16T20:35:24Z [done] — Root cause (integration-mismatch): scaffold_opencode получил параметр output_mode в сигнатуре, но вызывающий диспетчер bootstrap.py его не передавал — параметр молча падал в дефолт "off", и OpenCode единственный из 5 IDE оставался без режима, при этом bootstrap печатал «Done!». Дефолтное значение параметра превратило пропущенный аргумент из ошибки в тихий no-op. Prevention: integration-тест, параметризованный по SCAFFOLD_IDES из кода (не по руками набранному списку), гоняющий настоящий bootstrap_ide для каждой IDE — новая IDE попадает под гард автоматически; плюс guard-the-guard тест, который краснеет, если у scaffolded-IDE не объявлен файл правил. Root cause (race-condition): «загадочный» откат bootstrap.py к состоянию HEAD/v1.6.1 (с потерей ВСЕЙ ветки OpenCode) устроили мои же ревью-агенты: в задании было «RUN things / reproduce / construct the exact broken input», а у tausik-reviewer есть Bash — они воспроизводили баги ПРЯМО В ЖИВОМ рабочем дереве и возвращали обратно; один не успел вернуть. Симптомы: скачки размера файла (13935↔13522), мигающий git status, integrity-проверка падала и через секунду проходила. Прогоны тестов, шедшие ОДНОВРЕМЕННО с ревью, были недостоверны. Prevention: ревью-агентам с Bash давать worktree-изоляцию (isolation:"worktree"), НИКОГДА живое дерево, в котором работаешь сам; перед доверием любому «зелёному» прогону убедиться, что параллельных мутирующих агентов нет.
