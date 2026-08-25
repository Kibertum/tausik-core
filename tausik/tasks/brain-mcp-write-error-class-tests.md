---
slug: brain-mcp-write-error-class-tests
title: "MEDIUM: тесты store_record с NotionAuthError/NotionRateLimitError"
status: done
epic: null
story: null
complexity: simple
role: qa
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "tests/test_brain_mcp_write.py"
scope_exclude: "scripts/brain_mcp_write.py, scripts/brain_fallback.py, scripts/brain_notion_client.py"
relevant_files:
  - "tests/test_brain_mcp_write.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T19:24:38Z"
---

## Goal

Текущий test_store_record_notion_error_propagates использует bare ConnectionError → ветки auth/rate_limit не покрыты. Добавить 2 теста с NotionAuthError и NotionRateLimitError(retry_after=42), assert error_category и retry_after пропадают в format_store_result

## Acceptance Criteria

1. Добавлен тест с NotionAuthError: store_record возвращает {status=notion_error, error_category='auth'}, format_store_result отрендерит auth-specific сообщение (упоминание "auth" или "integration token")
2. Добавлен тест с NotionRateLimitError(retry_after=42): result['retry_after']==42, format_store_result содержит "Retry in 42 seconds"
3. Ошибка/граничный случай: NotionRateLimitError БЕЗ retry_after (None) → format_store_result использует дефолт (60 секунд), не крашится
4. FakeClient расширен для приёма конкретного exception instance (не ломает существующие тесты с raise_on_create=True)
5. Импорт NotionAuthError/NotionRateLimitError из brain_notion_client
6. pytest tests/test_brain_mcp_write.py проходит; ruff clean
7. Существующий test_store_record_notion_error_propagates остаётся зелёным (не регрессия)

## Plan

## Rollback

## Journal

- 2026-04-24T19:21:01Z [implementation] — AC verified: FakeClient расширен raise_error=Exception (существующий raise_on_create=True не тронут, test_notion_error_propagates PASS). Добавлено 3 теста: notion_auth_error_classified (error_category='auth', format содержит 'auth failed'), rate_limit_with_retry_after (retry_after==42, format: '42 seconds'), rate_limit_without_retry_after_uses_default (retry_after=None, format содержит 'Retry in' + 'seconds', не крашится). pytest 37/37 passed. ruff clean.
