---
slug: userpromptsubmit-hook
title: "UserPromptSubmit hook (intent detection → nudge)"
status: done
epic: claude-hardening
story: p1-runtime-enforcement
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/user_prompt_submit.py (новый), bootstrap/bootstrap_generate.py (generate_settings_claude), bootstrap/bootstrap_qwen.py (generate_settings_qwen), .claude/settings.json (dogfooding), tests/test_user_prompt_submit_hook.py (новый)"
scope_exclude: "session_start.py, task_gate.py, bash_firewall.py — существующие hooks не трогать. Template bootstrap_templates.py — не трогать. Другие bootstrap функции — не трогать."
relevant_files:
  - "scripts/hooks/user_prompt_submit.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - ".claude/settings.json"
  - "tests/test_user_prompt_submit_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T21:32:04Z"
---

## Goal

Детектить coding intent ("напиши", "fix", "добавь") и инжектить напоминание проверить активную задачу / создать task. KAIROS-стиль проактивный pinger

## Acceptance Criteria

1) Новый скрипт scripts/hooks/user_prompt_submit.py создан: читает prompt из stdin (JSON), детектит coding-intent ключевыми словами ("напиши", "fix", "add", "сделай", "implement", "create", "write", "refactor" и т.п.), при отсутствии active task инжектит reminder через hookSpecificOutput.additionalContext. 2) Hook зарегистрирован в bootstrap_generate.py (generate_settings_claude) и bootstrap_qwen.py как UserPromptSubmit hook, и в .claude/settings.json для dogfooding. 3) Skip-flag TAUSIK_SKIP_HOOKS=1 → exit 0. 4) Graceful degradation: нет БД/CLI → exit 0 без шума. 5) False-positive防护: не срабатывает на обычные вопросы ("что такое", "как работает", "explain", "show me"). 6) Non-blocking: hook всегда exit 0 (только nudge, не блокирует). 7) Новые pytest тесты (минимум 6): intent detection (positive + negative), no-task reminder, active-task пропускает, skip flag, no DB, malformed stdin. 8) pytest all passed. 9) ruff clean. Negative: (a) пустой/невалидный stdin JSON → exit 0 silent. (b) prompt с эмодзи/спецсимволами не падает. (c) prompt на неизвестном языке (не RU/EN) — не падает, используется keyword matching без ошибок.

## Plan

[{"step": "\u0421\u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a coding-intent keywords (RU+EN) + anti-false-positive list", "done": true}, {"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c scripts/hooks/user_prompt_submit.py: intent detection + active task check + JSON output", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c generate_settings_claude + generate_settings_qwen + .claude/settings.json", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c tests/test_user_prompt_submit_hook.py (6+ \u0442\u0435\u0441\u0442\u043e\u0432)", "done": true}, {"step": "pytest + ruff + \u0436\u0438\u0432\u043e\u0439 smoke-test \u043d\u0430 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u0438\u0445 \u0442\u0438\u043f\u0430\u0445 \u043f\u0440\u043e\u043c\u043f\u0442\u043e\u0432", "done": true}, {"step": "task log + task done", "done": true}]

## Rollback

## Journal

- 2026-04-16T21:28:56Z [implementation] — AC verified: AC1 (script + intent detection) ✓ — scripts/hooks/user_prompt_submit.py 130 строк с CODING_INTENT_KEYWORDS (RU+EN) и QUESTION_PATTERNS для anti-false-positive. AC2 (регистрация) ✓ — test_claude_settings_has_userpromptsubmit + test_qwen_settings_has_userpromptsubmit passed, .claude/settings.json обновлён. AC3 (skip-flag) ✓ — test_skip_flag_bypasses passed. AC4 (graceful degradation) ✓ — test_no_db_exits_silently + active-task skip без CLI. AC5 (no false-positive на вопросы) ✓ — test_question_about_code_does_not_nudge + test_explain_prompt_does_not_nudge. AC6 (non-blocking exit 0) ✓ — все 13 тестов проверяют returncode==0. AC7 (6+ тестов) ✓ — 13 тестов: TestIntentDetection (5) + TestActiveTaskCheck (1) + TestGracefulDegradation (5) + TestSettingsGeneration (2). AC8 (pytest passed) ✓ — 963/963 passed (было 950, +13 новых). AC9 (ruff clean) ✓ — All checks passed. Negative: (a) malformed stdin ✓. (b) emoji/special chars ✓. (c) japanese prompt ✓ — не падает, нет keyword match → no nudge.
