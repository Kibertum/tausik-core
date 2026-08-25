---
slug: sessionstart-hook
title: "Добавить SessionStart hook (auto-inject state)"
status: done
epic: claude-hardening
story: p0-foundation-rewrite
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/session_start.py (новый), bootstrap/bootstrap_generate.py (generate_settings_claude), bootstrap/bootstrap_qwen.py (generate_settings_qwen), .claude/settings.json (dogfooding), tests/test_session_start_hook.py (новый)"
scope_exclude: "Другие hooks (task_gate, bash_firewall, git_push_gate, auto_format, session_metrics) — не трогать. Другие bootstrap функции — не трогать."
relevant_files:
  - "scripts/hooks/session_start.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - ".claude/settings.json"
  - "tests/test_session_start_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T21:03:04Z"
---

## Goal

При старте сессии Claude Code автоматически получает состояние: active tasks, blocked, handoff highlights, session duration, dead ends. Без ручного /start

## Acceptance Criteria

1) Новый скрипт scripts/hooks/session_start.py создан: читает .tausik/tausik.db, запрашивает статус/active/blocked задачи, выдаёт context для инъекции в сессию. 2) Hook зарегистрирован в bootstrap_generate.py (generate_settings_claude) и bootstrap_qwen.py (generate_settings_qwen) как SessionStart hook. 3) Вывод в формате Claude Code: JSON с hookSpecificOutput.additionalContext ИЛИ plain text to stdout. 4) Skip-flag: TAUSIK_SKIP_HOOKS=1 env var → hook возвращает 0 без работы. 5) Graceful degradation: если .tausik/tausik.db не существует ИЛИ CLI недоступен → exit 0 без ошибки. 6) Timeout: <5s чтобы не тормозить старт сессии. 7) Новые pytest тесты: test_session_start_no_db (не падает без БД), test_session_start_with_db (выдаёт context), test_session_start_skip_flag (TAUSIK_SKIP_HOOKS=1 → empty). 8) .claude/settings.json обновлён: SessionStart hook добавлен. 9) Все существующие тесты passed. 10) ruff clean. Negative: (a) БД отсутствует → exit 0 без вывода. (b) CLI subprocess таймаут → exit 0 без вывода. (c) Невалидный CLAUDE_PROJECT_DIR env → использовать os.getcwd() fallback.

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c scripts/hooks/session_start.py (\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0411\u0414 + \u0441\u0431\u043e\u0440 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f + JSON output)", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c generate_settings_claude \u0432 bootstrap_generate.py", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c generate_settings_qwen \u0432 bootstrap_qwen.py", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c .claude/settings.json (\u0434\u043b\u044f dogfooding)", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c tests/test_session_start_hook.py", "done": true}, {"step": "pytest + ruff + smoke-test bootstrap", "done": true}, {"step": "task log + task done", "done": true}]

## Rollback

## Journal

- 2026-04-16T20:59:49Z [implementation] — AC verified: AC1 (scripts/hooks/session_start.py создан) ✓ — 94 строки, собирает status + active + blocked + reminders. AC2 (зарегистрирован в bootstrap_generate + bootstrap_qwen) ✓ — test_claude_settings_has_sessionstart + test_qwen_settings_has_sessionstart passed. AC3 (формат Claude Code hookSpecificOutput) ✓ — test_output_is_valid_json_when_present парсит JSON, проверяет hookEventName==SessionStart и additionalContext. AC4 (TAUSIK_SKIP_HOOKS=1 → exit 0 silent) ✓ — test_skip_flag_bypasses passed. AC5 (graceful degradation без БД) ✓ — test_exits_zero_when_no_db + test_db_present_but_no_cli passed. AC6 (timeout <5s) ✓ — в hook timeout=4s для subprocess, в settings.json timeout=6s. AC7 (новые тесты) ✓ — 8 тестов в tests/test_session_start_hook.py, все passed. AC8 (.claude/settings.json обновлён) ✓ — SessionStart hook добавлен с абсолютным путём. AC9 (все существующие passed) ✓ — 950/950 passed in 195s (было 942 → +8 новых). AC10 (ruff clean) ✓ — All checks passed. Negative: (a) отсутствие БД ✓. (b) CLI timeout/missing ✓. (c) пустой CLAUDE_PROJECT_DIR → os.getcwd() fallback, test_invalid_project_dir_env passed. БОНУС: Live smoke-test против реальной .tausik.db показал корректный JSON вывод с Tasks: 299/317, Session: #24, active task list.
