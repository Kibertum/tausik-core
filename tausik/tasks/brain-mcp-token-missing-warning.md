---
slug: brain-mcp-token-missing-warning
title: "MEDIUM: warning в search/get когда token unset"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "agents/claude/mcp/brain/handlers.py, agents/cursor/mcp/brain/handlers.py, tests/test_brain_mcp_handlers.py"
scope_exclude: "scripts/brain_mcp_read.py, scripts/brain_mcp_write.py, scripts/brain_runtime.py, scripts/brain_config.py"
relevant_files:
  - "agents/claude/mcp/brain/handlers.py"
  - "agents/cursor/mcp/brain/handlers.py"
  - "tests/test_brain_mcp_handlers.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T19:19:19Z"
---

## Goal

search/get молча передают client=None при отсутствии токена → пользователь не отличает offline от no-token. Добавлять explicit warning в результат когда cfg.enabled=true но client=None

## Acceptance Criteria

1. handle_brain_search с cfg.enabled=True и client=None (токен не в env) возвращает результат с явным warning, упоминающим имя env-переменной из cfg.notion_integration_token_env
2. handle_brain_get с cfg.enabled=True и client=None возвращает аналогичный warning
3. При client != None warning не добавляется (status quo сохранён)
4. Ошибка/граничный случай: при cfg.enabled=False warning НЕ добавляется — возвращается существующий "Brain is not enabled" hint, не сломан
5. Ошибка/граничный случай: если cfg.notion_integration_token_env отсутствует или пуст, warning содержит generic fallback текст вместо crash
6. Тесты в tests/test_brain_mcp_handlers.py покрывают search + get с token missing, и negative case (disabled → no warning)
7. agents/claude/mcp/brain/handlers.py и agents/cursor/mcp/brain/handlers.py синхронизированы (отличаются только docstring)
8. pytest tests/test_brain_mcp_handlers.py проходит; ruff clean

## Plan

## Rollback

## Journal

- 2026-04-24T19:15:35Z [implementation] — AC verified: добавлен _token_missing_warning(cfg) в оба handlers.py (claude+cursor, diff только docstring). Warning инжектится в result['warnings'] search и в warnings tuple get когда client is None. 6 новых тестов в tests/test_brain_mcp_handlers.py: token_missing_emits_warning×2, token_present_no_warning×2 (status quo), disabled_no_token_warning (AC 4 negative), without_env_name_fallback (AC 5 boundary). pytest 16/16 passed. ruff clean.
