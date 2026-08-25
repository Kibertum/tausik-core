---
slug: p0-defect-qg-2-git-diff-cross-check-created-at-sta
title: "[P0] Defect: QG-2 git-diff cross-check использует created_at вместо started_at"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_cli_verify.py, scripts/service_gates.py, tests/"
scope_exclude: null
relevant_files:
  - "scripts/project_cli_verify.py"
  - "scripts/service_gates.py"
  - "tests/test_qg2_window_started_at.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-11T23:37:53Z"
---

## Goal

Cross-check verify-кэша (is_declared_consistent_with_git_diff) берёт task.created_at как нижнюю границу git log --since. Для backlog-задач, созданных за дни/сессии до начала работы, в actual попадают файлы всех промежуточных чужих коммитов → declared никогда не покрывает их → перманентный cache_status=git-mismatch, verify-run не записывается, task_done блокируется. Воспроизведено на v15p-fix-rag-reindex-hang (коммит 831f03e попал в окно). Фикс: callers (project_cli_verify.py:48, service_gates.py:85,194) передают started_at с fallback на created_at; docstring verify_git_diff уже говорит "since task start".

## Acceptance Criteria

1. Callers cross-check'а передают started_at (fallback created_at, если started_at пуст). 2. Регрессионный тест: задача с created_at до чужого коммита и started_at после него проходит cross-check при declared = реально изменённые файлы. 3. Существующие тесты verify_git_diff зелёные. 4. bootstrap перегенерировал .claude; после правки scripts/ MCP считается drifted — verify/task_done через CLI.

## Plan

## Rollback

## Journal

- 2026-06-11T23:37:27Z [implementation] — Фикс: 3 call-site (project_cli_verify.py:48, service_gates.py:85+194) теперь передают started_at or created_at в git-diff cross-check. Тест tests/test_qg2_window_started_at.py: prefer started_at, fallback created_at, source-инвариант на всех callers. 126 passed (вместе с test_service_verification + test_verify_git_diff_stdin). ruff/mypy clean, bootstrap перегенерирован. MCP drifted (service_gates.py) — закрытие через CLI.
- 2026-06-11T23:37:53Z [implementation] — AC verified: 1. ✓ 3 call-site передают started_at or created_at (project_cli_verify.py, service_gates.py x2). 2. ✓ tests/test_qg2_window_started_at.py::test_verify_window_prefers_started_at + fallback-тест + source-инвариант. 3. ✓ 126 passed (test_service_verification, test_verify_git_diff_stdin, новый файл). 4. ✓ bootstrap перегенерировал .claude; закрытие через CLI из-за MCP drift.
