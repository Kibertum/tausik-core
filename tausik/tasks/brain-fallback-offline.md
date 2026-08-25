---
slug: brain-fallback-offline
title: "Graceful fallback когда brain не настроен / недоступен"
status: done
epic: shared-brain
story: brain-onboarding-docs
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_fallback.py (новый), agents/claude/mcp/brain/handlers.py (улучшенные messages, использование classify_error), agents/cursor/mcp/brain/handlers.py (зеркало), tests/test_brain_fallback.py (новый), небольшие правки в tests/test_brain_mcp_handlers.py для проверки новых сообщений"
scope_exclude: "Write queue, auto-disable config mutation, retry logic — отдельные задачи"
relevant_files:
  - "scripts/brain_fallback.py"
  - "scripts/brain_notion_client.py"
  - "scripts/brain_mcp_write.py"
  - "scripts/brain_mcp_read.py"
  - "agents/claude/mcp/brain/handlers.py"
  - "agents/cursor/mcp/brain/handlers.py"
  - "tests/test_brain_fallback.py"
  - "tests/test_brain_mcp_read.py"
  - "tests/test_brain_mcp_write.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T15:06:33Z"
---

## Goal

Если brain.enabled=false — MCP-tools возвращают "brain disabled, use `tausik brain init`". Если Notion недоступен (network/5xx) — fallback на local mirror + warning. Ни в одном случае агент не должен падать или блокировать основной флоу.

## Acceptance Criteria

1) scripts/brain_fallback.py (new, ~80 LOC): classify_error(exc) → "auth" | "not_found" | "rate_limit" | "network" | "server" | "unknown"; user_message(category, detail) → friendly markdown.
2) When brain.enabled=false, handlers.py возвращает "_Brain is not enabled. Run `.tausik/tausik brain init`._" — уже есть, сохраняем.
3) При NotionAuthError (401/403) в store-операциях: handler возвращает "_Notion auth failed — integration token is invalid or revoked. Re-run `.tausik/tausik brain init` or rotate the integration._" (не мутируем config, только сообщение).
4) При NotionRateLimitError: "_Rate-limited by Notion. Retry in N seconds._" (N из Retry-After если есть, иначе 60).
5) При NotionError сетевого происхождения (network/5xx): для search/get → возврат local-only результатов + warning "offline — showing local mirror only"; для store → "_Network unavailable — write not persisted to Notion. Try again when online._" (AC: не блокирует и не падает).
6) Без token в env: сообщение "_Brain integration token env var X is not set. Export your Notion token and retry._" — уже есть, сохраняем.
7) ≥10 тестов: classify_error для каждой категории (NotionAuthError, NotionNotFoundError, NotionRateLimitError, NotionServerError, NotionError-wrapping-URLError, generic); user_message для 3 категорий; handler_* интеграция проверяет что auth / network / rate_limit → разные markdown outputs; store flow: network error → friendly message.
8) mypy + ruff clean; 1456+ pytest green.
9) OOS: write queue / retry-later / автоматическое disable brain / retry на network error (эти — отдельные задачи).

## Plan

[{"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c scripts/brain_fallback.py: classify_error + user_message", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c handlers.py (claude+cursor): catch NotionError \u0432 _handle_store \u0438 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c classify_error", "done": true}, {"step": "tests/test_brain_fallback.py (>=10 \u0442\u0435\u0441\u0442\u043e\u0432)", "done": true}, {"step": "mypy + ruff + pytest", "done": true}, {"step": "/review + \u043f\u0440\u0430\u0432\u043a\u0438", "done": true}, {"step": "task done + commit", "done": true}]

## Rollback

## Journal

- 2026-04-23T14:58:46Z [implementation] — AC verified: 1. brain_fallback.classify_error + user_message + retry_after_from (pure, type-based) ✓ 2. Disabled: _not_configured_msg обновлён "run tausik brain init" без "coming soon", claude+cursor зеркало идентично ✓ 3. Auth message → "re-run tausik brain init" ✓ 4. Rate-limit: "Retry in N seconds" с N=Retry-After или 60 по умолчанию (test_user_message_rate_limit_defaults_to_60s + test_user_message_rate_limit_honors_retry_after) ✓ 5. Network: NotionNetworkError new type в brain_notion_client (вместо string-match); classify_error распознаёт по типу; user_message для store = "not persisted", для search/get = "local mirror only" (test_classify_network_by_type) ✓ 6. Token missing: сообщение сохранено ✓ 7. 21 тест в test_brain_fallback.py (было ≥10): classify для 6 типов исключений + user_message для 4 категорий + store integration + retry_after extraction + op validation ✓ 8. /review iterate: H1 (error_category rename), H2 (retry_after honored), M2 (NotionNetworkError по типу), M3 (tightened assertions), L1 ("coming soon" убрано), M1 (imports hoisted) — fixed. 9. OOS: write queue, auto-disable, retry — не тронуто.
