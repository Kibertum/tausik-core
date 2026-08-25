---
slug: v14-pricing-table-config
title: "config.json: тарифы $/1M по model_id"
status: done
epic: v14-cost-telemetry
story: v14-cost-schema
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_config.py docs/en/cli.md docs/ru/cli.md tests/test_llm_pricing_config.py"
scope_exclude: null
relevant_files:
  - "scripts/project_config.py"
  - "tests/test_llm_pricing_config.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T10:53:57Z"
---

## Goal

Валидация конфига и значение по умолчанию UNKNOWN.

## Acceptance Criteria

1. Схема ключей и пример. 2. Валидация при load. 3. Negative: отрицательная цена отвергается.

## Plan

## Rollback

## Journal

- 2026-05-01T10:53:57Z [implementation] — AC verified: 1. ✓ Схема llm_pricing_usd_per_million + пример в EN/RU cli.md. 2. ✓ sanitize в load_config (normalize_llm_pricing_config). 3. ✓ Negative: отрицательные и NaN/skipped — lookup UNKNOWN=None. Tests: pytest tests/test_llm_pricing_config.py.
