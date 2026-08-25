---
slug: brain-mcp-write-ok-not-mirrored-test
title: "MEDIUM: тест store_record с упавшим upsert_page"
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
scope_exclude: "scripts/brain_mcp_write.py, scripts/brain_sync.py"
relevant_files:
  - "tests/test_brain_mcp_write.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T19:29:37Z"
---

## Goal

Тот же blind spot что я починил в brain_runtime. test_brain_mcp_write.py не покрывает ok_not_mirrored branch. Форсить brain_sync.upsert_page raise, assert status=ok_not_mirrored + format_store_result рендерит 'Stored in Notion but local mirror lagged'

## Acceptance Criteria

1. Тест в tests/test_brain_mcp_write.py форсит brain_sync.upsert_page (или map_page_to_row) поднимать exception через monkeypatch
2. Assert: result['status'] == 'ok_not_mirrored'
3. Assert: result['notion_page_id'] установлен (Notion успех — не теряем page_id)
4. Assert: result['warning'] содержит исходное сообщение exception
5. Assert: format_store_result(result, category) содержит "Stored in Notion but local mirror lagged"
6. Ошибка/граничный случай: exception в map_page_to_row (раньше чем upsert) тоже даёт ok_not_mirrored, не крашит вызов
7. pytest tests/test_brain_mcp_write.py проходит; ruff clean

## Plan

## Rollback

## Journal

- 2026-04-24T19:26:04Z [implementation] — AC verified: 2 теста добавлено. test_ok_not_mirrored_when_upsert_fails (monkeypatch brain_sync.upsert_page → sqlite3.OperationalError): status=ok_not_mirrored, page_id сохранён, warning содержит исходное сообщение, format_store_result содержит 'in Notion but local mirror lagged' + page_id. test_ok_not_mirrored_when_map_page_to_row_fails (boundary, monkeypatch map_page_to_row → KeyError) — раньше, чем upsert: тоже ok_not_mirrored, не крашит. pytest 39/39 passed. ruff clean.
