---
slug: qg2-cannot-close-fileless-task
title: "QG-2 не умеет закрывать задачу, которая законно не трогает файлов (и контракт описывает старое поведение)"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/verify_git_diff.py (git-порцелейн-хелпер), scripts/gate_verify_first.py (ветка no_file_changes), scripts/service_task_done.py + service_task.py + service_gates.py (проброс флага + запись колонки), CLI-парсер task done, harness/claude/mcp/project/handlers.py (+ .claude-зеркало через bootstrap), новая миграция колонки, docs/ru+en/agent-contract.md, tests/*"
scope_exclude: "Не трогать логику changed_files_since (git log --since) — она для другого контракта; не менять поведение обычного пути (пустой relevant_files без флага блокирует); не расширять флаг на проекты без verify-гейтов (там пустая область и так закрывается)"
relevant_files:
  - "scripts/verify_git_diff.py"
  - "scripts/gate_verify_first.py"
  - "scripts/service_gates.py"
  - "scripts/service_task_done.py"
  - "scripts/service_task_done_flags.py"
  - "scripts/service_task.py"
  - "scripts/project_backend.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v41.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-20T22:54:28Z"
---

## Goal

НАЙДЕНО НА СЕБЕ в сессии #121: задача l26-roots-premise-fix выполнена полностью (8 из 8 AC) и не может быть закрыта. Переведена в blocked.

ДЕФЕКТ 1 — ГЛАВНЫЙ. task done требует непустой relevant_files: «an undeclared scope is unknown, not verified empty». Правило верное (память #226, решение #150) и неполное: у него ДВА состояния вместо трёх. Есть «объявлено» и «не объявлено», но нет «ПРОВАБЕЛЬНО ПУСТО» — задача не тронула ни одного файла, и это ДОКАЗАНО чистым git status, а не умолчано.

Класс задач, попадающих в дыру, фреймворк сам же и поощряет: конвенция #251 предписывает держать планирование и отчётность ВНУТРИ фреймворка, а не в файлах. Значит любая задача переформулирования постановок, любая чисто-планировочная работа и любое решение через tausik decide сегодня НЕ ЗАКРЫВАЕМЫ штатным путём. Флаг --no-tests-expected не спасает: он про «файлы есть, тестов у них нет».

ЧЕМ ЭТО ОПАСНО. Агент, упёршийся в это, имеет ровно три выхода, и два из них плохие: объявить относящимися файлы, которых не касался (подписать квитанцию на чужое — ровно тот обход узкой областью, против которого стоит git-mismatch), закрыть в обход QG-2, либо оставить выполненную задачу висеть. Дыра толкает к первому.

ЧТО СДЕЛАТЬ. Третье состояние области, симметричное тому, как no_tests_declared сделан отдельной колонкой (а не значением scope): объявление «эта задача не меняет файлов», проверяемое ФАКТОМ (git status по дереву пуст либо diff по объявленным каталогам пуст), а не словом агента. Проверяемость здесь обязательна: необязательное объявление немедленно станет способом закрывать что угодно. Записывать так же, как no_tests_declared, — счётно, чтобы такие закрытия можно было пересчитать запросом.

ДЕФЕКТ 2 — ПОПУТНЫЙ, ОТДЕЛЬНЫЙ. docs/ru/agent-contract.md:23-24 описывает поведение, отменённое в сессии #118 (verify-cache-empty-scope-hit): «Без relevant_files (None/empty) — fallback на полный suite остаётся». Код блокирует. Свежий агент, доверившийся контракту, ожидает полный прогон и получает отказ. Проверить EN-зеркало docs/en/. Чинить не только текстом: расхождение доки и поведения обязано ловиться гейтом, иначе вернётся.

## Acceptance Criteria

AC1. Новый флаг task done --no-file-changes (CLI + MCP), проброшен по цепочке task_done→_task_done_report→_run_quality_gates_report→_enforce_verify_first→enforce_verify_first. Третье состояние области, НЕ значение scope.
AC2. Проверяемость ФАКТОМ: с флагом закрытие разрешено ТОЛЬКО если git status --porcelain по объявленной области пуст (relevant_files как pathspec; всё дерево при пустом relevant_files). git недоступен ИЛИ область грязна → БЛОК с actionable-сообщением. Объявление без git-доказательства не закрывает никогда.
AC3. Не-вакуумность: доказано тестом — грязное дерево (или грязный объявленный путь) блокирует flagged-close; флаг не может стать универсальным «закрыть что угодно».
AC4. Счётность: fileless-закрытия пишутся в отдельную колонку tasks.no_file_changes_declared (симметрично no_tests_declared), запрашиваемо: SELECT * FROM tasks WHERE no_file_changes_declared=1.
AC5. Демонстрация e2e: тест доказывает, что при чистой области flagged-close проходит, колонка выставлена, гейты области НЕ гонялись (нечего гонять). l26-roots-premise-fix закрывается этим путём после чистки дерева (реальное закрытие — за владельцем на релизном коммите).
AC6. Дефект 2: docs/ru/agent-contract.md:23-24 и EN-зеркало исправлены — пустой relevant_files БЛОКИРУЕТ (не fallback на полный suite).
AC7. Doc-drift гейт/тест: падает, если устаревшая формулировка «fallback на полный suite» вернётся в контракт; привязывает доку к поведению.
AC8. Регресс: обычный путь без флага не изменён (пустой relevant_files без флага блокирует как раньше); полный suite зелёный в обоих режимах.

## Plan

## Rollback

git revert коммита задачи откатывает флаг, колонку-миграцию и правки гейта/доков разом. Миграция колонки чисто аддитивна (ADD COLUMN NOT NULL DEFAULT 0) — откат схемы не требуется, старый код игнорирует колонку. При откате переоткрыть задачу: без флага fileless-задачи снова незакрываемы, а исправленный контракт разойдётся с вернувшимся поведением.

## Journal

- 2026-07-20T22:50:53Z [implementation] — Реализовано: флаг task done --no-file-changes (третье состояние области QG-2). git-хелпер uncommitted_changes() (porcelain, scoped pathspec, fail-closed→None) в verify_git_diff.py; ветка _enforce_no_file_changes в gate_verify_first.py; проброс no_file_changes через service_gates(_run_quality_gates_report short-circuit + _enforce_verify_first)→service_task_done(колонка на commit)→service_task.task_done; миграция v41 tasks.no_file_changes_declared + baseline schema + backend allowlist; CLI --no-file-changes + MCP handler/tool schema. Дефект 2: docs/ru/agent-contract.md исправлен (пустой relevant_files БЛОКИРУЕТ, а не fallback), EN-зеркала agent-contract нет. Doc-drift тест ловит возврат устаревшей формулировки. 17 новых тестов (test_fileless_close.py). Починены test-side заглушки: conftest _noop(**kwargs), fake_report. bootstrap --ide all прогнан (drift none). Полный suite: 5156 passed после регенерации doc-constants (test_count 5272→5320). doctor OK.
- 2026-07-20T22:51:54Z [implementation] — AC verified: 1. флаг --no-file-changes проброшен CLI+MCP→task_done→_task_done_report→_run_quality_gates_report→_enforce_verify_first→enforce_verify_first (TestFilelessGateBranch). 2. git-проверка ФАКТОМ, fail-closed: dirty→block, git None→block (test_dirty_scope_blocks, test_unverifiable_git_fails_closed). 3. Не-вакуумность: грязное дерево блокирует (test_dirty_scope_blocks). 4. Колонка tasks.no_file_changes_declared: test_clean_scope_closes_and_records_column, test_fresh_db_has_column. 5. e2e: чистая область закрывает, гейты НЕ гонятся run_gates.assert_not_called (test_clean_scope_closes_and_records_column). 6. docs/ru/agent-contract исправлен (test_contract_states_the_real_behavior). 7. doc-drift ловит устаревшую формулировку (test_stale_full_suite_fallback_claim_is_gone). 8. Регресс: без флага пустая область блокирует как раньше (test_flag_off_still_blocks_empty_scope) + полный suite 5156 passed.
- 2026-07-20T22:54:27Z [implementation] — AC verified 1-8: флаг --no-file-changes проброшен CLI+MCP→enforce_verify_first; git-проверка ФАКТОМ fail-closed (dirty/None→block); не-вакуумность (грязное дерево блокирует); колонка no_file_changes_declared счётна; e2e чистая область закрывает без гейтов (run_gates.assert_not_called); docs/ru контракт исправлен + doc-drift тест; регресс без флага блокирует; 17 новых тестов + полный suite 5156 passed. Извлечён service_task_done_flags.py под filesize-гейт.
- 2026-07-20T22:54:49Z [done] — AC evidence (markers): AC-1 ✓ флаг проброшен по всей цепочке — TestFilelessGateBranch + e2e. AC-2 ✓ git ФАКТОМ, fail-closed — test_dirty_scope_blocks, test_unverifiable_git_fails_closed. AC-3 ✓ не-вакуумность — грязное дерево/None блокируют. AC-4 ✓ колонка no_file_changes_declared — test_clean_scope_closes_and_records_column, test_fresh_db_has_column. AC-5 ✓ e2e чистая область закрывает, гейты не гонятся — run_gates.assert_not_called. AC-6 ✓ docs/ru контракт — test_contract_states_the_real_behavior. AC-7 ✓ doc-drift — test_stale_full_suite_fallback_claim_is_gone. AC-8 ✓ регресс — test_flag_off_still_blocks_empty_scope + full suite 5156 passed. Domain: закрытие fileless-задачи безопасно в РЕАЛЬНОМ дереве — накопление правок других задач (19 файлов) корректно блокирует whole-tree close (fail-closed), доказано на живом verify #1113 (NOTE о 19 undeclared). L26-roots-premise-fix закроется этим путём после релизного коммита (чистое дерево).
