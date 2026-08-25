---
slug: keyword-detector-hook
title: "Keyword-detector hook на вывод агента"
status: done
epic: claude-hardening
story: p1-runtime-enforcement
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/keyword_detector.py (новый), bootstrap/bootstrap_generate.py (Stop hook registration), bootstrap/bootstrap_qwen.py, .claude/settings.json, tests/test_keyword_detector_hook.py (новый)"
scope_exclude: "Существующие hooks не трогать. bootstrap_templates.py не трогать."
relevant_files:
  - "scripts/hooks/keyword_detector.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - ".claude/settings.json"
  - "tests/test_keyword_detector_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T21:42:56Z"
---

## Goal

Детектить фразы-маркеры в выводе ("I'll implement", "Let me code") и инжектить напоминание о task/AC. Из oh-my-claudecode

## Acceptance Criteria

1) Новый скрипт scripts/hooks/keyword_detector.py создан как Stop hook. Читает transcript_path из stdin, находит последнее assistant-сообщение, детектит drift-маркеры ("I'll implement", "Let me code", "I will now write", "напишу сейчас", "реализую это", "приступаю к реализации" и т.п.). 2) При обнаружении drift И отсутствии active TAUSIK task → возвращает JSON {"decision":"block","reason":"..."} что заставляет агента продолжить с инъекцией reminder. 3) Anti-infinite-loop: проверяет stop_hook_active в входном JSON — если true, exit 0 без действий. 4) Зарегистрирован в bootstrap_generate.py (generate_settings_claude), bootstrap_qwen.py (generate_settings_qwen), .claude/settings.json как Stop hook. 5) TAUSIK_SKIP_HOOKS=1 → exit 0. 6) Graceful degradation: нет БД/transcript невалиден/пустой → exit 0. 7) Новые pytest тесты (8+): detect drift keyword + no task → block response; active task → no block; stop_hook_active → no-op; skip flag; malformed transcript; empty transcript; no drift keyword → no-op; JSON schema validation of block response. 8) pytest all passed. 9) ruff clean. Negative: (a) transcript_path не существует → exit 0 silent. (b) transcript невалидный JSONL → exit 0. (c) последнее сообщение не assistant → exit 0. (d) stop_hook_active=true → exit 0 без работы (защита от рекурсии).

## Plan

[{"step": "\u0421\u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c DRIFT_KEYWORDS (RU+EN)", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c scripts/hooks/keyword_detector.py: \u0447\u0442\u0435\u043d\u0438\u0435 transcript + last assistant message + block response", "done": true}, {"step": "\u0417\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c Stop hook \u0432 bootstrap_generate + bootstrap_qwen + .claude/settings.json", "done": true}, {"step": "tests/test_keyword_detector_hook.py (8+ \u0442\u0435\u0441\u0442\u043e\u0432)", "done": true}, {"step": "pytest + ruff + live smoke", "done": true}, {"step": "log + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T21:39:53Z [implementation] — AC verified: AC1 (Stop hook с drift detection) ✓ — scripts/hooks/keyword_detector.py с 10+ drift patterns RU+EN (I'll implement/let me code/сейчас напишу/реализую и т.п.). AC2 (block response при drift+no-task) ✓ — test_english_drift_with_no_task_blocks + test_russian_drift_with_no_task_blocks парсят JSON и проверяют decision=block, reason содержит SENAR Rule 1. AC3 (anti-infinite-loop через stop_hook_active) ✓ — test_stop_hook_active_short_circuits. AC4 (регистрация в 3 местах) ✓ — test_claude_settings_has_stop_hook + test_qwen_settings_has_stop_hook. AC5 (skip flag) ✓ — test_skip_flag passed. AC6 (graceful degradation) ✓ — test_no_db + test_missing_transcript + test_malformed_stdin + test_transcript_without_assistant_does_not_block. AC7 (8+ тестов) ✓ — 13 тестов: TestDriftDetection (4) + TestLoopSafety (1) + TestGracefulDegradation (6) + TestSettingsGeneration (2). AC8 (pytest passed) ✓ — 976/976 passed (было 963, +13 новых). AC9 (ruff clean) ✓ — All checks passed. Negative: (a) transcript_path отсутствует → exit 0 ✓. (b) невалидный JSONL → exit 0 ✓. (c) только user messages в transcript → exit 0 ✓. (d) stop_hook_active=true → exit 0 ✓. БОНУС: поддержка nested message format (Claude transcripts иногда используют {'message':{'role':...}}) через test_nested_message_format. СЛОВАРЬ: DRIFT_KEYWORDS покрывает "I'll implement/code/write/create/build/add/refactor/fix" + "Let me..." + "I will..." + "I'm going to..." + "Going to..." + "Next step is to..." + русские "сейчас напишу/реализую/добавлю/создам/исправлю/запилю" + "приступаю к реализации/написанию" + "давайте напишем/реализуем" + "я напишу/реализую".
