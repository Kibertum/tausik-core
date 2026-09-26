---
slug: v14-hygiene-cli-stub
title: "Подкоманда hygiene с dry-run и --confirm"
status: done
epic: v14-project-hygiene
story: v14-hygiene-automation
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_cli_hygiene.py"
  - "tests/test_hygiene_cli.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T11:11:28Z"
---

## Goal

Безопасное обслуживание без silent delete.

## Acceptance Criteria

1. Команда или заготовка. 2. Dry-run по умолчанию. 3. Negative: без --confirm деструктивные операции не выполняются.

## Plan

## Rollback

## Journal

- 2026-05-02T11:11:18Z [implementation] — AC-1: tausik hygiene archive подкоманда (parser add_hygiene + project_cli_hygiene.cmd_hygiene). AC-2: dry-run по умолчанию - archive list печатает кандидатов без записей; tested via tests/test_hygiene_cli.py::TestCmdHygieneArchive::test_dry_run_lists_candidates. AC-3 negative: tausik_utils.ServiceError raised при --confirm в v1 (no destructive op exists yet); tested via tests/test_hygiene_cli.py::TestNegativeConfirmRejected::test_confirm_fails_fast.
- 2026-05-02T11:11:27Z [implementation] — AC verified: 1. ✓ tausik hygiene archive subcmd (project_cli_hygiene.py + parser add_hygiene). 2. ✓ Dry-run by default tested via tests/test_hygiene_cli.py::test_dry_run_lists_candidates. 3. ✓ Negative: --confirm raises ServiceError tested via tests/test_hygiene_cli.py::test_confirm_fails_fast.
- 2026-08-26T09:33:41Z [done] — СВЕРКА ССЫЛКИ, аудит closure-evidence, сессия #186. Процитированные при закрытии tests/test_hygiene_cli.py::test_confirm_fails_fast и ::TestNegativeConfirmRejected в файле отсутствуют, история их знала — то есть это настоящая гниль. Автоматический кандидат test_confirm_idempotent ОТКЛОНЁН при ручной сверке: он проверяет повторный прогон как no-op, а не быстрый отказ; это другая проверка, а не то же самое под новым именем. Преемник не назначен, ссылка остаётся в отчёте аудита как неразрешимая. Кандидат от схожести имён не является основанием — этого требует AC-8 задачи closure-evidence-references-rot-and-nothing-notices.
- 2026-09-26T19:02:57Z [done] — EVIDENCE-RETIRED: tests/test_hygiene_cli.py::test_confirm_fails_fast — successor test_confirm_idempotent asserts a different property; member gone since 2765980f (feat(v14b-polish-round-1): B5 hygiene archive + B9 memory cl)
