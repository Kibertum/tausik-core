---
slug: stop-hook
title: "Stop hook (проверка открытых задач/explorations)"
status: done
epic: claude-hardening
story: p2-quality-loops
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/session_cleanup_check.py (новый), bootstrap/bootstrap_generate.py (добавление второго Stop hook), bootstrap/bootstrap_qwen.py, .claude/settings.json, tests/test_session_cleanup_check.py (новый)"
scope_exclude: "keyword_detector.py (первый Stop hook) — не трогать. Другие hooks — не трогать."
relevant_files:
  - "scripts/hooks/session_cleanup_check.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - ".claude/settings.json"
  - "tests/test_session_cleanup_check.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T22:36:12Z"
---

## Goal

Перед остановкой агент получает напоминание о незакрытых задачах, открытых explorations, несохранённых dead-ends. Предлагает /checkpoint или /end

## Acceptance Criteria

1) Новый Stop hook scripts/hooks/session_cleanup_check.py, который при завершении turn-а агента выводит предупреждение в stderr (non-blocking) если: (a) есть открытая exploration, (b) есть review-задачи, (c) сессия идёт >150 мин (близко к 180-лимиту). 2) Anti-spam: проверяет stop_hook_active чтобы не выводить повторно. 3) Зарегистрирован как второй Stop hook в bootstrap_generate + bootstrap_qwen + .claude/settings.json (первый — keyword_detector.py для drift). 4) TAUSIK_SKIP_HOOKS=1 → exit 0. 5) Graceful: нет БД/CLI → exit 0. 6) Всегда exit 0 (non-blocking). 7) Новые pytest тесты (6+): exploration reminder, review-tasks reminder, session timeout reminder, skip flag, no DB, multiple warnings комбинируются. 8) pytest all passed. 9) ruff clean. Negative: (a) нет БД → silent. (b) CLI timeout → silent. (c) пустой tausik status → silent.

## Plan

[{"step": "scripts/hooks/session_cleanup_check.py: exploration/review/timeout \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438", "done": true}, {"step": "\u0420\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u0432\u0442\u043e\u0440\u043e\u0433\u043e Stop hook \u0432 3 \u043c\u0435\u0441\u0442\u0430\u0445", "done": true}, {"step": "tests/test_session_cleanup_check.py (6+ \u0442\u0435\u0441\u0442\u043e\u0432)", "done": true}, {"step": "pytest + ruff", "done": true}, {"step": "log + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T22:26:24Z [implementation] — AC verified: AC1 (Stop hook scripts/hooks/session_cleanup_check.py) ✓ — 122 строки, 3 проверки: open exploration, tasks in review, session >150 min. AC2 (stop_hook_active guard) ✓ — test_stop_hook_active_short_circuits passed. AC3 (регистрация как second Stop hook) ✓ — test_claude_settings_has_cleanup_hook + test_qwen_settings_has_cleanup_hook проверяют что оба (keyword_detector + cleanup) зарегистрированы. AC4 (skip flag) ✓. AC5 (graceful) ✓ — test_no_db_exits_silently + test_db_present_but_no_cli + test_malformed_stdin. AC6 (non-blocking exit 0) ✓. AC7 (6+ тестов) ✓ — 17 тестов: TestPureHelpers (9) + TestHookIntegration (6) + TestSettingsGeneration (2). AC8 (pytest passed) ✓ — 1020/1020 passed in 209s (было 1003, +17 новых). AC9 (ruff clean) ✓. Negative: (a) нет БД ✓. (b) CLI недоступен ✓. (c) malformed stdin ✓.
