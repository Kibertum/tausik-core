---
slug: notification-hooks
title: "Notification hooks (Telegram/Discord/Slack)"
status: done
epic: claude-hardening
story: p3-nice-to-have
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/notifier.py (новый), scripts/hooks/notify_on_done.py (новый), tests/test_notifier.py (новый)"
scope_exclude: "Регистрация hook в bootstrap settings — опциональная, т.к. требует явной env var, не включаем по умолчанию"
relevant_files:
  - "scripts/notifier.py"
  - "scripts/hooks/notify_on_done.py"
  - "tests/test_notifier.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T23:49:52Z"
---

## Goal

Конфигурируемые webhook-хуки на события: session end, task done, gate failure. Из oh-my-claudecode

## Acceptance Criteria

1) Утилита scripts/notifier.py с функцией send_notification(text, kind) — отправляет POST на webhook URL из env vars TAUSIK_SLACK_WEBHOOK, TAUSIK_DISCORD_WEBHOOK, TAUSIK_TELEGRAM_WEBHOOK. 2) Формирует правильный payload для каждого типа: Slack {text}, Discord {content}, Telegram — через Bot API URL формата https://api.telegram.org/bot<TOKEN>/sendMessage. 3) Non-blocking: ошибки сети/4xx/5xx не падают, возвращают False. 4) PostToolUse hook scripts/hooks/notify_on_done.py — отправляет уведомление после tausik_task_done если webhook configured. 5) pytest test_notifier.py — 5+ тестов с mocked urllib: slack format, discord format, telegram format, no webhook → noop, network error → graceful. 6) pytest all passed. 7) ruff clean. Negative: (a) webhook URL пустой → no-op, не падает. (b) urllib.error.URLError → поймать, вернуть False, залогировать stderr. (c) 4xx/5xx response → вернуть False.

## Plan

[{"step": "scripts/notifier.py \u0441 send_notification()", "done": true}, {"step": "scripts/hooks/notify_on_done.py", "done": true}, {"step": "tests/test_notifier.py \u0441 mocked urllib", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T23:46:51Z [implementation] — AC verified: AC1 (send_notification) ✓ — scripts/notifier.py с send_slack/discord/telegram и fan-out. AC2 (payloads) ✓ — test_slack_posts_text_field (text), test_discord_posts_content_field (content), test_telegram_posts_text_field passed. AC3 (non-blocking) ✓ — test_network_error_returns_false + test_4xx_response_returns_false — ловят URLError, HTTPError, OSError, TimeoutError. AC4 (PostToolUse hook) ✓ — scripts/hooks/notify_on_done.py; test_non_task_done_tool_exits_silently. AC5 (5+ тестов) ✓ — 10 тестов: TestChannels (5) + TestErrorHandling (2) + TestFanout (2) + TestHookScript (1). AC6 (pytest) ✓ — 1089/1089 passed in 183s (+10 новых). AC7 (ruff clean) ✓. Negative: (a) пустой webhook URL (whitespace) → no-op ✓. (b) URLError → False + stderr log ✓. (c) 4xx/5xx status → False ✓.
