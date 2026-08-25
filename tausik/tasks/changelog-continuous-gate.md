---
slug: changelog-continuous-gate
title: "Гейт непрерывного CHANGELOG: task done блокируется без записи в changelog"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: null
defect_of: null
scope: "scripts/gate_changelog.py (new), scripts/service_gates.py, scripts/service_task_done.py, scripts/service_task.py, scripts/project_parser_task.py, scripts/project_cli_task.py, harness/claude/mcp/project/handlers.py, harness/claude/mcp/project/tools.py, docs/ru/agent-contract.md, .tausik/config.json, CHANGELOG.md, CHANGELOG.ru.md, tests/test_changelog_gate.py (new)"
scope_exclude: "gate_verify_first.py behavior (no_file_changes path untouched), verify cache, risk/l3 logic, other gates"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/ru/agent-contract.md"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/service_gates.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "tests/conftest.py"
  - "tests/test_tausik_service.py"
  - "scripts/gate_changelog.py"
  - "tests/test_changelog_gate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-22T18:47:33Z"
---

## Goal

Сделать дисциплину непрерывного changelog (Decision #161, convention #275) механически неотменяемой, а не держащейся на строке в acceptance_criteria. Хук на закрытии задачи проверяет, что рабочее дерево содержит diff в CHANGELOG.md И зеркале CHANGELOG.ru.md; если записи нет — блокирует task done с понятным сообщением (fail-closed). Для задач, легально не меняющих поведение (доки, чистка, замер), предусмотреть явный override-флаг по образцу --no-file-changes, чтобы гейт не деформировал честные исключения.

## Acceptance Criteria

AC1. Хук на пути task done: при попытке закрыть задачу без флага-исключения проверяет через git наличие изменений в CHANGELOG.md И зеркале CHANGELOG.ru.md; при отсутствии — блокирует с сообщением, называющим оба файла и флаг-исключение.
AC2. Флаг-исключение (по образцу --no-file-changes, для fileless и no-behavior задач) пропускает проверку и пишет в журнал явную причину; молчаливого обхода нет.
AC3. Fail-closed: ошибка самого хука (git недоступен и т.п.) блокирует закрытие, а не пропускает — по образцу whole-tree proof (решение #157).
AC4. Тест fail-then-pass: задача, изменившая оба changelog-файла, закрывается; не изменившая — блокируется; с флагом-исключением — закрывается.
AC5. docs/ru/agent-contract.md описывает новое поведение гейта и флаг-исключение (иначе свежий агент упрётся в блок без объяснения — класс дефекта doc-behavior-drift).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert the commit. Gate is config-gated (task_done.changelog_gate.enabled) — set enabled=false in .tausik/config.json to disable without revert. Per-task escape: --no-changelog flag.

## Journal

- 2026-07-22T18:04:56Z [planning] — Design: config-driven changelog gate (mechanism generic / policy configured). New module gate_changelog.py::enforce_changelog called from _run_quality_gates_report on trigger==task-done. Reads config.task_done.changelog_gate {enabled(default False), files[]}. When enabled: git-proves EACH configured file has uncommitted changes via verify_git_diff.uncommitted_changes (union pathspec); missing→block naming files+flag; git None→fail-closed (whole-tree-proof #157). Per-task escape --no-changelog logs supervision bypass event (no silent bypass, l26-bypass-telemetry). no_file_changes tasks already return early at service_gates.py:207 → naturally exempt. Default OFF so framework doesn't block projects w/o bilingual changelog; TAUSIK's own .tausik/config.json enables it with [CHANGELOG.md, CHANGELOG.ru.md]. Threading: parser→cli→task_done→_task_done_report→_run_quality_gates_report→enforce_changelog + MCP handlers/tools.
- 2026-07-22T18:44:25Z [implementation] — AC verified: 1. ✓ enforce_changelog блокирует при отсутствии diff в CHANGELOG.md И CHANGELOG.ru.md, называя оба файла + флаг (test_neither_file_dirty_blocks_naming_both, test_one_file_missing_blocks_naming_it). 2. ✓ --no-changelog пропускает + пишет счётное событие bypass_changelog_gate, молчаливого обхода нет (test_no_changelog_flag_skips_and_logs_bypass). 3. ✓ Fail-closed: git=None или нет проектного каталога → блок (test_git_none_fails_closed, test_no_project_dir_fails_closed). 4. ✓ Fail-then-pass через _run_quality_gates_report: neither→block, both→pass, --no-changelog→pass (TestWiring). 5. ✓ docs/ru/agent-contract.md описывает гейт+флаг (TestDocDrift). Final: оба CHANGELOG обновлены прозой; гейт само-верифицируется на этом закрытии. Full suite 5362 passed.
- 2026-07-22T18:47:31Z [implementation] — AC1-5 verified via tests/test_changelog_gate.py (20 tests) + TestWiring; docs/ru/agent-contract.md updated; both CHANGELOG files carry prose entry (gate self-verifies this close). Full suite 5362 passed. Filesize: service_task.py + service_task_done.py trimmed back to 400 via comment compression (behavior unchanged).
