---
slug: brain-runtime-status-handling
title: "Fix ok_not_mirrored + scrub_blocked handling in brain_runtime"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/brain_runtime.py, tests/test_service_knowledge_decide.py"
scope_exclude: "scripts/service_knowledge.py (routing logic verified as correct), scripts/brain_mcp_write.py (source of status codes — contract is the fix target, not the change target)"
relevant_files:
  - "scripts/brain_runtime.py"
  - "tests/test_service_knowledge_decide.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T10:32:03Z"
---

## Goal

Убрать двойную запись decision в Notion+SQLite при status='ok_not_mirrored' и корректно формировать сообщение для scrub_blocked (issues вместо error)

## Acceptance Criteria

AC1: try_brain_write_decision возвращает (True, page_id) при status='ok_not_mirrored' — decision НЕ пишется в локальную БД.
AC2: try_brain_write_decision возвращает (False, 'scrub_blocked: <issues>') при status='scrub_blocked' — issues list из result['issues'] отображается в сообщении, а не generic 'unknown'.
AC3: Тест scrub_blocked мокает brain_mcp_write.store_record (не саму try_brain_write_decision) — реально прогоняет формирование сообщения.
AC4: Новый тест: ok_not_mirrored → AssertTrue(be.decision_add НЕ вызван), msg содержит 'saved to brain'.
AC5: Все существующие 15 тестов test_service_knowledge_decide.py остаются зелёными.
AC6: pytest tests/test_service_knowledge_decide.py -v → 100% pass.
AC7: ruff + mypy scripts/ clean.

## Plan

## Rollback

## Journal

- 2026-04-24T10:28:14Z [implementation] — AC1 verified: ok_not_mirrored теперь возвращает (True, page_id). Новый тест test_brain_ok_not_mirrored_treated_as_success подтверждает — decision НЕ пишется локально (len(svc.decisions())==0).
- 2026-04-24T10:28:16Z [implementation] — AC2 verified: scrub_blocked теперь возвращает 'scrub_blocked: filesystem_paths, slug_markers' — issues list корректно разворачивается в сообщение. Проверяется ассертом 'unknown' not in msg.
- 2026-04-24T10:28:18Z [implementation] — AC3 verified: test_brain_scrub_blocked_falls_back_local теперь мокает brain_mcp_write.store_record (не try_brain_write_decision) — реально прогоняет join(issues) формат.
- 2026-04-24T10:28:20Z [implementation] — AC5-6 verified: pytest tests/test_service_knowledge_decide.py -v → 16/16 pass (15 исходных + 1 новый ok_not_mirrored тест).
- 2026-04-24T10:28:20Z [implementation] — AC7 verified: ruff check scripts/brain_runtime.py tests/test_service_knowledge_decide.py → All checks passed. mypy scripts/ → Success: no issues found in 62 source files.
- 2026-04-24T10:28:37Z [implementation] — Regression check: 129/129 pass (test_tausik_service, test_memory_block, test_e2e_workflow, test_edge_cases, test_cascade_delete). Word 'recorded' в ответе svc.decide() сохранён — backward-compat с 6 existing тест-файлами цел.
- 2026-04-24T10:28:44Z [implementation] — AC verified: 1. ok_not_mirrored→(True,page_id), decision_add НЕ вызван ✓ 2. scrub_blocked возвращает 'scrub_blocked: <issues list>', не 'unknown' ✓ 3. test мокает brain_mcp_write.store_record одним слоем глубже ✓ 4. новый test_brain_ok_not_mirrored_treated_as_success ✓ 5. все 15 существующих тестов остались зелёными ✓ 6. pytest test_service_knowledge_decide.py → 16/16 pass ✓ 7. ruff + mypy scripts/ clean ✓
- 2026-04-24T10:32:12Z [done] — Root cause: brain_runtime.try_brain_write_decision был написан по наивной модели "status=ok → success, иначе failure" без сверки с контрактом brain_mcp_write.store_record. store_record возвращает 3 success-подобных варианта: ok (полный), ok_not_mirrored (Notion принял, local mirror упал) и structured errors (scrub_blocked с issues, notion_error с error_category). format_store_result в том же файле уже обрабатывает ok_not_mirrored как успех — это была единственная референсная точка, её пропустили при написании helper'a. Urok: при вынесении wrapper'a над существующей функцией — открывать файл source-of-status-codes и копировать contract полностью, не угадывать по имени status.
