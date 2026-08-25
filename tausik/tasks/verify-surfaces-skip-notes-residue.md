---
slug: verify-surfaces-skip-notes-residue
title: "Остатки после фикса MCP-verify: NOTE про пустую область срабатывает на полном прогоне, а gate_runner всё ещё пишет «All gates passed» после SKIP"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "harness/claude/mcp/project/handlers.py (items 1,3), scripts/gate_runner.py (item 2), scripts/service_task_done.py (item 4), tests/test_mcp_verify_handler.py + gate_runner test"
scope_exclude: "MCP verify tool schema (не добавляем no_tests_expected — вне области), service_gates.run_verify_for_task (сигнатура не меняется)"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "docs/_generated/constants.json"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "harness/claude/mcp/project/handlers.py"
  - "scripts/gate_runner.py"
  - "scripts/hooks/bash_cmd_norm.py"
  - "scripts/hooks/bash_cmd_scan.py"
  - "scripts/hooks/hook_supervision.py"
  - "scripts/hooks/rm_wipe_detect.py"
  - "scripts/hooks/secret_scan.py"
  - "scripts/service_task_done.py"
  - "tests/test_bypass_telemetry.py"
  - "tests/test_gates.py"
  - "tests/test_hooks.py"
  - "tests/test_mcp_verify_handler.py"
  - "tests/test_secret_scan_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T16:24:53Z"
---

## Goal

Два остатка, найденных ревью сессии #133 на фикс mcp-verify-hides-gate-skip. (1) _handle_verify поддерживает task_slug=None (полный suite — задокументированный паритет с CLI). В этом режиме service_gates выставляет files=[], поэтому новая NOTE печатается ВСЕГДА и говорит «no relevant_files declared for this task … tausik task update <slug> --relevant-files» — с литеральным <slug> и при отсутствии задачи. Самая широкая верификация, которую предлагает инструмент, теперь заканчивается неисполнимым выговором. Нужно `if task_slug and not result.get("relevant_files")` и отдельная формулировка для беззадачного пути. (2) scripts/gate_runner.py: `python scripts/gate_runner.py review --files ...` печатает «[SKIP] pytest», а затем «All gates passed.» — ровно тот дефект, ради прекращения которого извлекался gate_verdict, в соседнем файле, не тронутый. (3) Побочно: ветка NOTE для status=="no-tests-declared" в _handle_verify недостижима, потому что _handle_verify никогда не передаёт no_tests_expected — либо пробросить параметр, либо убрать мёртвую ветку. (4) Побочно: _cl_block присваивается и не используется в scripts/service_task_done.py:180 (предсуществующее; ветка ключуется на _cl_msg).

## Acceptance Criteria

1. _handle_verify: NOTE «no relevant_files declared for this task … <slug>» больше НЕ печатается на беззадачном полном прогоне (task_slug=None); гейтится на `if task_slug and not result.get("relevant_files")`; для беззадачного пути — отдельная корректная формулировка (не выговор с литеральным <slug>). 2. gate_runner.main(): после [SKIP] gate больше НЕ печатает «All gates passed.» — сообщение честно отражает пропуск (все пропущены → «no gate executed»; часть пропущена → называет пропущенные), паритет с gate_verdict/verify-pipeline. 3. Мёртвая ветка status=="no-tests-declared" в _handle_verify удалена (недостижима: _handle_verify не передаёт no_tests_expected, единственный триггер). 4. service_task_done.py: _cl_block используется (ветка на флаге блокировки, а не на пустоте сообщения) — нет assigned-but-unused. 5. Тесты на (1) и (2); полная суита зелёная, 0 warnings.

## Plan

## Rollback

git revert; изменения локальны и аддитивно-корректирующие (условие NOTE, сообщение, удаление мёртвой ветки, использование существующего флага).

## Journal

- 2026-07-26T16:24:51Z [implementation] — AC verified: 1. ✓ test_mcp_verify_handler.py::test_taskless_full_suite_has_no_scoped_scolding (no <slug>, full-suite note) + test_scoped_empty_names_the_real_task (real slug 't') 2. ✓ test_gates.py::TestGateRunnerCliVerdict::test_all_skipped_run_does_not_claim_pass — subprocess: [SKIP] pytest, no 'All gates passed.', 'no gate actually executed' present 3. ✓ no-tests-declared branch removed from _handle_verify (dead: run_verify_for_task no_tests_expected default False, never passed by handler; sole trigger of that status) 4. ✓ service_task_done.py now branches on cl_block flag; cl_msg used only as message text — no assigned-but-unused 5. ✓ tausik_verify high pytest PASS over 7 mapped files; test_mcp_verify_handler+test_gates 109 passed; deployed handler matches source; constants matching
