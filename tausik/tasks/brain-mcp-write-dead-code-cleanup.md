---
slug: brain-mcp-write-dead-code-cleanup
title: "LOW: убрать dead fallback result.get('category')"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/brain_mcp_write.py, tests/test_brain_mcp_write.py"
scope_exclude: "scripts/brain_fallback.py"
relevant_files:
  - "scripts/brain_mcp_write.py"
  - "tests/test_brain_mcp_write.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T19:33:55Z"
---

## Goal

format_store_result читает error_category или category, но store_record пишет только error_category. Dead branch скроет будущие typos. Убрать or result.get('category')

## Acceptance Criteria

1. format_store_result строка `cat = result.get("error_category") or result.get("category") or "unknown"` упрощена до `cat = result.get("error_category") or "unknown"`
2. Существующий test_format_result_notion_error остаётся зелёным (тестирует payload без error_category — должен идти в "unknown")
3. Ошибка/граничный случай: payload с typo `category` (вместо `error_category`) теперь даёт 'unknown' (раньше скрывал typo) — добавлен явный тест
4. pytest tests/test_brain_mcp_write.py проходит; ruff clean
5. Никаких других изменений в format_store_result

## Plan

## Rollback

## Journal

- 2026-04-24T19:30:30Z [implementation] — AC verified: scripts/brain_mcp_write.py:379 — убрано 'or result.get("category")', осталось 'cat = result.get("error_category") or "unknown"'. Добавлен test_format_result_typo_category_falls_back_to_unknown — payload с typo `category` (вместо `error_category`) теперь идёт в unknown renderer, не в auth. Существующий test_format_result_notion_error PASS. pytest 40/40 passed. ruff clean.
