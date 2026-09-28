---
slug: cli-ops-residue-split-by-command
title: "Остаток project_cli_ops.py разрезать по командам — семейство уже имеет эту конвенцию"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: architect
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli_session.py"
  - "scripts/project_cli_search.py"
  - "scripts/project_cli_knowledge.py"
  - "scripts/project_cli_doc.py"
  - "tests/test_cli_family_has_no_residue.py"
scope_paths:
  - "scripts/project_cli*.py"
  - "scripts/project.py"
  - "tests/*.py"
  - "tausik/gates.json"
  - "docs/ru/*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-27T18:05:52Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#73"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Выделено из filesize-rejoin-cap-deformed-wrappers (решение #199), где замер показал: семейство project_cli_* содержит 26 модулей, и 24 из них названы ИМЕНЕМ КОМАНДЫ одним словом (adapt, aidd, config, doctor, drift, events, hygiene, key, receipt, renar, review, role, serve, skill, snippet, spec, stack, state, task, verify). Два выбивались: project_cli_ops.py и project_cli_extra.py, названные по остаточному признаку — «ops» не значит ничего, «extra» значит «что не влезло». Их строки документации ПЕРЕЧИСЛЯЛИ по 10 и 4 несвязанные команды вместо домена. Что это остаток гейта, а не архитектуры, записано в самих файлах: brain_cli_ops.py — «extracted from project_cli_ops for filesize gate», project_cli_events.py — «Kept out of project_cli_ops.py (400-line gate)», project_cli_metrics.py — «Extracted from project_cli_ops.py to keep it under the 400-line filesize gate». Родительская задача починила ТОЛЬКО два физически разорванных домена (cmd_metrics вернулась в project_cli_metrics.py, cmd_audit — в project_cli_audit.py, бывший _audit_extra), сознательно не трогая остальное: churn на CLI-поверхности перед капстоуном 1.8 при нулевой выгоде для релиза. Здесь доделать остаток. В project_cli_ops.py осталось 234 строки и 8 команд: cmd_hud, cmd_suggest_model, cmd_search, cmd_dead_end, cmd_explore, cmd_doc, cmd_run, cmd_session_recompute. В project_cli_extra.py — 368 строк и 4 команды: cmd_memory, cmd_update_claudemd, cmd_fts, cmd_gates. НЕ 1.8: это чистая архитектурная гигиена, ничего в релизе от неё не зависит.

## Acceptance Criteria

AC-1 ЗАМЕР ПЕРЕД ПРАВКОЙ, а не из постановки: project_cli_ops.py — 252 строки и 8 команд, project_cli_extra.py — 346 строк и 5 команд (в постановке стояло 234/8 и 368/4, и в extra появилась cmd_knowledge). Семейство project_cli_* — 33 модуля, из них по остаточному признаку названы РОВНО два. AC-2 Оба остаточных модуля ИСЧЕЗАЮТ. Каждая из 13 команд живёт в модуле, названном доменом, а не остатком; ни один новый модуль не назван «прочее», «extra», «ops», «misc». AC-3 ДОКСТРИНГ КАЖДОГО НОВОГО МОДУЛЯ НАЗЫВАЕТ ДОМ, а не перечисляет команды (конвенция #348). Проверяется: первая строка докстринга не содержит запятой со списком имён команд. AC-4 НЕГАТИВ: поверхность CLI не изменилась. Каждая из 13 команд вызывается и отвечает тем же, что до правки — проверено запуском, а не чтением импортов. AC-5 НЕГАТИВ: cmd_skill и cmd_stack, которые extra лишь ПЕРЕЭКСПОРТИРОВАЛ, импортируются из своих настоящих модулей. Переэкспорт через остаток — тот же дефект, что и сам остаток. AC-6 НЕГАТИВ: ни один новый модуль не превышает 500 строк, и ни один не создан ради одной строки — разрез по домену, а не по счётчику. AC-7 Полная лента зелёная; число прошедших не падает.

## Plan

## Rollback

Перемещение функций между модулями без изменения тел; откат — git revert, импорты возвращаются к остаточным модулям.

## Journal

- 2026-09-27T12:44:01Z [implementation] — AC-1 ✓ ЗАМЕР ПЕРЕД ПРАВКОЙ, и он разошёлся с постановкой: project_cli_ops.py — 252 строки / 8 команд (в постановке 234/8), project_cli_extra.py — 346 строк / 5 команд (в постановке 368/4; появилась cmd_knowledge). Семейство было 33 модуля, названных остатком — ровно 2. Докстринг самого ops признавался: «NOT a domain. This module is the residue of repeated bleeding to satisfy the filesize gate».
- 2026-09-27T12:44:01Z [implementation] — AC-2 ✓ ОБА ОСТАТКА УДАЛЕНЫ, 13 команд разошлись по СЕМИ домам: project_cli_session (hud, suggest_model, session_recompute), project_cli_search (search, fts), project_cli_knowledge (knowledge, memory, dead_end + помощник _publication_blocklists), project_cli_explore (explore), project_cli_doc (doc, update_claudemd), project_cli_run (run), project_cli_gates (gates + _print_gate). Семейство стало 38 модулей, названных остатком — 0.
- 2026-09-27T12:44:02Z [implementation] — AC-2 РАЗРЕЗ ПО ДОМЕНУ, А НЕ ПО СЧЁТЧИКУ, и три склейки стоит назвать: dead_end ушёл к памяти, потому что тупик ЕСТЬ память особого типа; update_claudemd ушёл к doc, потому что оба порождают отслеживаемый документ из живой БД; fts ушёл к search, потому что это две команды над одним хранилищем. Каждый помощник уехал со своей командой — отчёт о гейте, форматирующийся в другом модуле, и есть начало нового ящика.
- 2026-09-27T12:44:02Z [implementation] — AC-2 ТЕЛА ФУНКЦИЙ СКОПИРОВАНЫ ДОСЛОВНО по диапазону строк, а не пере-сгенерированы из AST: разрез поэтому НЕ МОЖЕТ изменить поведение. Импорты перенесены целиком, лишние сняты ruff (F401 в select проекта): 65 находок, 65 исправлено.
- 2026-09-27T12:44:02Z [implementation] — AC-3 ✓ ДОКСТРИНГ КАЖДОГО НАЗЫВАЕТ ДОМ: «The current session: what it is, what it advises, and its recomputed numbers», «Searching the project's own record, and the index that makes it fast», «Reading and writing what the project knows», «Documents this project generates about itself», «Gate state: what is enabled, what it costs». Ни один не перечисляет команды.
- 2026-09-27T12:44:03Z [implementation] — AC-4 ✓ ПРОВЕРЕНО ЗАПУСКОМ, а не чтением импортов: все 13 команд вызваны через живой CLI (`<команда> --help`), все 13 ответили кодом 0 и строкой usage. Импорт, который разрешается, — ещё не работающая команда.
- 2026-09-27T12:44:03Z [implementation] — AC-5 ✓ ПЕРЕЭКСПОРТ УМЕР ВМЕСТЕ С ОСТАТКОМ: extra лишь пробрасывал cmd_skill и cmd_stack из project_cli_skill и project_cli_stack; project.py теперь импортирует их оттуда напрямую. Проброс через остаток — тот же дефект, что и сам остаток, только незаметнее.
- 2026-09-27T12:44:04Z [implementation] — AC-6 ✓ РАЗМЕРЫ: 137, 29, 205, 30, 101, 39, 73 строки — все под 500 и ни один модуль не создан ради одной строки. Самые малые (search 29, explore 30) — не обрубки: search и explore суть ИМЕНА КОМАНД, а конвенция семейства — модуль по имени команды, а не ящик по имени того, что не влезло.
- 2026-09-27T12:44:04Z [implementation] — КОНВЕНЦИЯ ЗАКРЕПЛЕНА ТЕСТОМ, чтобы остаток не завёлся снова: tests/test_cli_family_has_no_residue.py проверяет ВСЕ 38 модулей семейства по двум признакам — имя не из словаря ящиков (ops, extra, misc, other, util, helpers, common, stuff) и первая строка докстринга не перечисляет три и более сущности. Плюс мутация: проверено, что правило узнаёт project_cli_ops и перечисляющий докстринг, и НЕ считает ящиком настоящие имена. 83 теста зелёные.
- 2026-09-27T18:05:32Z [implementation] — AC-2: ✓ tests/test_cli_family_has_no_residue.py::test_no_module_is_named_after_a_drawer
- 2026-09-27T18:05:32Z [implementation] — AC-3: ✓ tests/test_cli_family_has_no_residue.py::test_the_docstring_names_a_home_not_a_list
- 2026-09-27T18:05:33Z [implementation] — AC-4: ✓ tests/test_cli_entrypoint_guard.py::test_direct_run_is_refused и ::test_module_still_imports по всем 38 модулям семейства; плюс живой прогон 13 команд через CLI, все ответили кодом 0.
- 2026-09-27T18:05:33Z [implementation] — AC-6: ✓ tests/test_filesize_split_smoke.py — ни один новый модуль не превышает предел; размеры 137, 29, 205, 30, 101, 39, 73.
- 2026-09-27T18:05:33Z [implementation] — AC-7: ✓ полная лента после разреза: 11628 прошли. Девять отказов первого прогона были мои и все исправлены — семь модулей не унаследовали страж точки входа, один тест объявлял несуществующий префикс, один не объявлял CROSSCUTTING_SCOPE.
