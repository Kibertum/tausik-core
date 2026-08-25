---
slug: verify-fix-loop
title: "Verify→fix loop после task done (Ralph-mode-lite)"
status: done
epic: claude-hardening
story: p1-runtime-enforcement
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/task_done_verify.py (новый), bootstrap/bootstrap_generate.py (добавление hook), bootstrap/bootstrap_qwen.py, .claude/settings.json, tests/test_task_done_verify_hook.py (новый)"
scope_exclude: "Другие hooks — не трогать. service_gates.py (QG-2) — не модифицировать, это параллельный слой."
relevant_files:
  - "scripts/hooks/task_done_verify.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - ".claude/settings.json"
  - "tests/test_task_done_verify_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T22:18:54Z"
---

## Goal

После task done --ac-verified запускается adversarial-review subagent, ищет 3 слабых места. Если найдено — loop fix → re-verify пока не пройдёт. Из oh-my-claudecode Ralph

## Acceptance Criteria

1) Новый PostToolUse hook scripts/hooks/task_done_verify.py: срабатывает на mcp__tausik-project__tausik_task_done и tausik_task_done tool calls. 2) После успешного task_done читает task notes + AC через CLI/DB, применяет 5 лёгких rule-based проверок качества evidence: (a) упомянуты file paths, (b) есть ✓/passed маркеры на каждый AC пункт, (c) есть числа/счётчики тестов, (d) есть ссылки на конкретные файлы или их секции, (e) упомянут lint/ruff статус. 3) Если 2+ проверки проваливаются — hook выводит предупреждение через stderr (non-blocking — agent не уходит в бесконечный цикл). 4) Зарегистрирован в bootstrap_generate.py + bootstrap_qwen.py + .claude/settings.json. 5) TAUSIK_SKIP_HOOKS=1 → exit 0. 6) Graceful: нет БД/CLI/невалидный JSON → exit 0. 7) Новые pytest тесты (8+): все 5 checks (pass + fail), threshold=2 failures → warning, TAUSIK_SKIP_HOOKS, no DB, malformed input, matcher не совпадает. 8) pytest all passed. 9) ruff clean. Negative: (a) tool_name не task_done → silent exit. (b) task_done завершился ошибкой → silent. (c) слишком длинные notes (>10KB) → truncate, не падает.

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c scripts/hooks/task_done_verify.py: PostToolUse matcher + \u0447\u0442\u0435\u043d\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438 \u0447\u0435\u0440\u0435\u0437 CLI + 5 rule-based \u043f\u0440\u043e\u0432\u0435\u0440\u043e\u043a", "done": true}, {"step": "\u0420\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f PostToolUse hook \u0432 bootstrap_generate + bootstrap_qwen + .claude/settings.json", "done": true}, {"step": "tests/test_task_done_verify_hook.py (8+ \u0442\u0435\u0441\u0442\u043e\u0432)", "done": true}, {"step": "pytest + ruff + live smoke-test \u043d\u0430 \u0440\u0435\u0430\u043b\u044c\u043d\u043e\u0439 \u0437\u0430\u0434\u0430\u0447\u0435", "done": true}, {"step": "task log + task done", "done": true}]

## Rollback

## Journal

- 2026-04-16T22:15:29Z [implementation] — AC verified: AC1 (PostToolUse hook scripts/hooks/task_done_verify.py) ✓ — 168 строк, matcher на mcp__tausik-project__tausik_task_done + Bash task done. AC2 (5 rule-based проверок) ✓ — _check_file_paths, _check_ac_checkmarks, _check_test_numbers, _check_file_references, _check_lint_status. Unit тесты test_strong_evidence_passes_all_checks (все 5 pass), test_empty_notes_fails_multiple_checks (≥4 fail), per-check tests. AC3 (threshold=2, non-blocking, stderr) ✓ — test_thin_evidence_produces_warning проверяет "TAUSIK verify-fix-loop" в stderr. AC4 (регистрация) ✓ — test_claude_settings_has_verify_hook + test_qwen_settings_has_verify_hook passed, .claude/settings.json обновлён. AC5 (skip flag) ✓. AC6 (graceful degradation) ✓ — test_no_db_exits_silently + test_malformed_stdin + test_tool_errored_exits_silently. AC7 (8+ тестов) ✓ — 15 тестов: TestHeuristics (6) + TestHookIntegration (7) + TestSettingsGeneration (2). AC8 (pytest) ✓ — 1003/1003 passed in 212s (было 988, +15 новых). AC9 (ruff clean) ✓. Negative: (a) non-matching tool → silent ✓. (b) tool errored → silent ✓. (c) oversize notes → truncate до 12KB, не падает ✓.
