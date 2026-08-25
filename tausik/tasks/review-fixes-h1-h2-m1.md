---
slug: review-fixes-h1-h2-m1
title: "Исправить находки /review: H1 (substring match), H2 (marker counting), M1 (duplicate helpers)"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: notification-hooks
scope: "scripts/hooks/_common.py (новый), scripts/hooks/notify_on_done.py, scripts/hooks/task_done_verify.py, scripts/hooks/keyword_detector.py, scripts/hooks/user_prompt_submit.py, scripts/hooks/session_start.py, scripts/hooks/session_cleanup_check.py, tests/test_task_done_verify_hook.py, tests/test_notifier.py"
scope_exclude: "M2-M5 и L1-L4 оставлены на отдельные задачи. Логика task_done_verify heuristics checks 3-5 не трогать"
relevant_files:
  - "scripts/hooks/_common.py"
  - "scripts/hooks/notify_on_done.py"
  - "scripts/hooks/task_done_verify.py"
  - "scripts/hooks/keyword_detector.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "scripts/hooks/session_start.py"
  - "scripts/hooks/session_cleanup_check.py"
  - "tests/test_task_done_verify_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-17T00:10:54Z"
---

## Goal

Устранить 2 High + 1 Medium реальных бага из /review эпика claude-hardening: false-positive bash detection, сломанный evidence-check, дублирование _tausik_path в 5 hooks

## Acceptance Criteria

1) H1: в scripts/hooks/notify_on_done.py и scripts/hooks/task_done_verify.py заменить substring check "task done" in command на regex-matcher scripts/hooks/_common.py is_task_done_bash_cmd() — проверяет реальный CLI shape (tausik/tausik.cmd с task done <slug>). 2) H2: в scripts/hooks/task_done_verify.py _check_ac_checkmarks: заменить loose substring на word-boundary regex (r"[✓✔]|\bpassed\b|\bverified\b|\bok\b|\bcomplete[d]?\b"), НЕ матчить 'complete' в 'incomplete'/'completion'. 3) M1: создать scripts/hooks/_common.py с tausik_path() + has_active_task() + is_task_done_bash_cmd(); keyword_detector/user_prompt_submit/session_start/session_cleanup_check/task_done_verify/notify_on_done импортируют из _common, не дублируют. 4) Все существующие pytest тесты passed после рефакторинга. 5) Новые тесты: test_false_positive_bash_task_done (echo/grep/git log НЕ матчится), test_ac_checkmarks_excludes_incomplete_completion. 6) ruff clean. Negative: (a) legitimate "tausik task done my-slug" — матчится. (b) "git log --grep=task done" — НЕ матчится. (c) prose "this is incomplete" — НЕ даёт marker count.

## Plan

[{"step": "scripts/hooks/_common.py: tausik_path + has_active_task + is_task_done_bash_cmd (regex)", "done": true}, {"step": "H2: \u0443\u0436\u0435\u0441\u0442\u043e\u0447\u0438\u0442\u044c _check_ac_checkmarks \u0447\u0435\u0440\u0435\u0437 re", "done": true}, {"step": "\u041c\u0438\u0433\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c 6 hooks \u043d\u0430 _common imports + H1 regex", "done": true}, {"step": "\u0420\u0430\u0441\u0448\u0438\u0440\u0438\u0442\u044c \u0442\u0435\u0441\u0442\u044b (false positive bash + incomplete/completion)", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-17T00:07:59Z [implementation] — AC verified: AC1 (H1 substring→regex) ✓ — scripts/hooks/_common.py _BASH_TASK_DONE_RE матчит только "tausik[.cmd] task done <slug>", не echo/grep/git log. AC2 (H2 word-boundary regex) ✓ — _AC_MARKER_RE в task_done_verify.py: r"[✓✔]|\b(passed|verified|ok|complete[d]?)\b" — "incomplete"/"completion" не матчатся благодаря \b. + _extract_notes_section отделяет notes от title/goal. AC3 (M1 _common.py) ✓ — 6 hooks мигрированы на from _common import: notify_on_done, task_done_verify, keyword_detector, user_prompt_submit, session_start, session_cleanup_check. AC4 (existing pytest) ✓ — 1095/1095 passed (было 1089, +6 новых). AC5 (новые regression тесты) ✓ — TestBashTaskDoneDetection (5: real, echo, grep, cmd variant, MCP) + test_ac_checkmarks_excludes_incomplete_and_completion. AC6 (ruff clean) ✓. Negative: (a) "tausik task done my-slug" → матчится. (b) 'echo "task done today"' → НЕ матчится (test_echo). (c) "This is incomplete. Completion pending." → 0 markers (test_ac_checkmarks_excludes).
- 2026-04-17T00:11:11Z [done] — Root cause: при писании 6 hook-файлов последовательно скопипастил _tausik_path и _has_active_task в каждый вместо выноса сразу в общий _common.py — convention #2 (Mixin composition pattern) не соблюдена с первого раза. + для bash task done detection использовал простой "in" substring match — не подумал про false positives (echo/grep). Предотвращение: при создании 2+ похожих hook-файлов сразу выносить общие helpers; для любой строковой проверки user input задать себе вопрос "какие невинные контексты матчатся?".
