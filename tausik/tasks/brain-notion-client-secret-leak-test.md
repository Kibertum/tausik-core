---
slug: brain-notion-client-secret-leak-test
title: "LOW: тест что Bearer token не echoed в errors/logs"
status: done
epic: null
story: null
complexity: simple
role: qa
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "tests/test_brain_notion_client.py"
scope_exclude: "scripts/brain_notion_client.py"
relevant_files:
  - "tests/test_brain_notion_client.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T19:39:04Z"
---

## Goal

Нет теста verifying что self._token не попадает в stdout/exception messages/error bodies. Добавить defensive test: инициализировать NotionClient с recognizable token, перехватить все outputs, assert token not in captured

## Acceptance Criteria

1. Тест(ы) в tests/test_brain_notion_client.py инициализируют NotionClient с уникально распознаваемым токеном (e.g., "secret_rec_TOKEN_AAA_DO_NOT_LEAK")
2. Assert: repr(client) не содержит токен
3. Assert: str(NotionAuthError) для 401 не содержит токен (и err.body не содержит)
4. Assert: str(NotionRateLimitError) для 429 не содержит токен
5. Assert: str(NotionServerError) для 5xx (retries exhausted) не содержит токен
6. Assert: str(NotionNetworkError) для URLError не содержит токен
7. Ошибка/граничный случай: caplog/captured log output во время retry ретраев не содержит токен
8. pytest tests/test_brain_notion_client.py проходит; ruff clean

## Plan

## Rollback

## Journal

- 2026-04-24T19:35:27Z [implementation] — AC verified: 7 defensive tests added using _LEAK_TOKEN="secret_rec_TOKEN_AAA_DO_NOT_LEAK_XYZ" и _leak_client() helper. Покрыто: repr(client), NotionAuthError (str+body), NotionNotFoundError, NotionRateLimitError (retries exhausted), NotionServerError, NotionNetworkError, retry_log через caplog (boundary: logger.warning не содержит токен). pytest 33/33 passed. ruff clean.
