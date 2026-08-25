---
slug: brain-decide-auto-route
title: "tausik decide использует classifier для auto-routing"
status: done
epic: shared-brain
story: brain-tausik-integration
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_knowledge.py (modify decide() + new private helper), tests/test_service_knowledge_decide.py (new)"
scope_exclude: "scripts/brain_mcp_write.py (reuse store_record), scripts/brain_classifier.py (reuse classify), scripts/brain_config.py (reuse load_brain), scripts/project_cli.py (cmd_decide call unchanged), agents/**/mcp/brain/handlers.py (не дедуплицировать _open_deps в этой задаче — scope creep)"
relevant_files:
  - "scripts/service_knowledge.py"
  - "scripts/brain_runtime.py"
  - "tests/test_service_knowledge_decide.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T09:50:27Z"
---

## Goal

Команда `tausik decide` прогоняет content через classifier. Записывает либо в local memory, либо в brain.decisions. Выводит маркер "→ saved to brain" / "→ saved to local" + причину решения. Без interactive prompt.

## Acceptance Criteria

1. svc.decide(text) без task_slug и с markers (через classify) → target=local, сообщение содержит "saved to local" + reason. 2. svc.decide(text) без task_slug и clean generic → target=brain при brain.enabled, сообщение содержит "saved to brain" + Notion page_id. 3. svc.decide(text) без task_slug и clean, brain disabled → local fallback, reason="brain not enabled". 4. svc.decide(text, task_slug=X) всегда → local, даже для clean generic (safeguard: task-linked decisions inherently project-specific). brain_runtime.try_brain_write_decision НЕ вызывается. 5. Brain write failure (notion_error/config_error/scrub_blocked/token missing) → local fallback, reason в сообщении указывает категорию ошибки. 6. Negative: пустой/whitespace text → local с reason="empty content" (classifier default safe, validate_length не проверяет пустоту — это актуальное поведение, не менялось). 7. Backward compat: существующие decide() тесты (test_tausik_service, test_e2e_workflow, test_memory_block, test_stress, test_edge_cases, test_cascade_delete) проходят без изменений — сообщение содержит "recorded", локальная запись в таблице decisions сохранена. 8. brain_runtime.try_brain_write_decision никогда не raises (missing token → False; NotionClient exception → False).

## Plan

[{"step": "\u0420\u0430\u0441\u0448\u0438\u0440\u0438\u0442\u044c service_knowledge.decide(): task_slug set \u2192 \u0444\u043e\u0440\u0441-local; \u0438\u043d\u0430\u0447\u0435 classify(text, 'decision', cfg=load_brain()) \u0438 \u0440\u043e\u0443\u0442\u0438\u043d\u0433", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c private helper _try_brain_write_decision(text, rationale, cfg): Notion client + SQLite conn + store_record. Return (True, msg)/(False, error_reason). Fail-safe \u2014 \u043b\u044e\u0431\u043e\u0439 exception \u2192 (False, str(e))", "done": true}, {"step": "\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u0444\u043e\u0440\u043c\u0430\u0442 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u044f: local \u2192 'Decision #N recorded \u2014 saved to local (reason).' / brain \u2192 'Decision recorded \u2014 saved to brain (reason). Page: {id}'. \u0421\u043b\u043e\u0432\u043e 'recorded' \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f \u0434\u043b\u044f backward compat", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c tests/test_service_knowledge_decide.py: task_slug force-local, clean \u2192 brain \u0441 mock client, clean \u2192 local fallback \u043f\u0440\u0438 disabled, brain_error \u2192 local fallback, empty \u2192 ServiceError, backward compat smoke test", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c pytest tests/test_service_knowledge_decide.py, pytest tests/ full (\u043d\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u0440\u0435\u0433\u0440\u0435\u0441\u0441\u0438\u0439), ruff \u0438 mypy scripts/", "done": true}, {"step": "\u041a\u043e\u043c\u043c\u0438\u0442: feat(brain): auto-route decide via classifier", "done": true}]

## Rollback

## Journal

- 2026-04-24T09:46:34Z [implementation] — AC verified: 1. markers content → saved to local с reason ✓ (test_content_with_src_file/abs_path/tausik_cmd_marker_routes_local) 2. clean + brain enabled → saved to brain + page_id ✓ (test_clean_content_brain_enabled_routes_brain) 3. clean + brain disabled → local fallback, reason="brain not enabled" ✓ (test_clean_content_brain_disabled_falls_back_local) 4. task_slug всегда local, brain_runtime НЕ вызван ✓ (test_task_slug_forces_local_even_for_clean + test_task_slug_forces_local_does_not_call_brain с mock.assert_not_called) 5. brain failure → local fallback с error category в msg ✓ (test_brain_write_failure + test_brain_scrub_blocked) 6. empty/whitespace → local с "empty content" ✓ 7. backward compat — msg содержит "recorded", decisions() табл сохранена ✓ 8. try_brain_write_decision never raises ✓ (missing token + NotionClient exception). Также: scripts/service_knowledge.py split — helper вынесен в новый scripts/brain_runtime.py (51 строка). service_knowledge.py стал 374 строки (было бы 410 без split — над 400-line gate). Retro-предсказание "pre-plan filesize check" сработало. Gates: - pytest tests/test_service_knowledge_decide.py: 15/15 pass - pytest tests/ full: 1514 passed, 2 skipped (было 1499 + 15 новых = 1514, регрессий ноль) - ruff check new/changed files: All checks passed - mypy scripts/: Success, no issues in 62 files
