---
slug: v14-bootstrap-context-tier
title: "Ключ context_tier: minimal/standard/full в генерации правил"
status: done
epic: v14-framework-lean
story: v14-lean-rules-layers
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_config.py bootstrap/ scripts/project_cli_doctor.py docs/en/quickstart.md docs/ru/quickstart.md tests/test_context_tier.py"
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "scripts/project_config.py"
  - "tests/test_context_tier.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T10:47:11Z"
---

## Goal

Меньше текста при minimal.

## Acceptance Criteria

1. Ключ в config и bootstrap. 2. Документация. 3. Negative: невалидное значение tier отвергается.

## Plan

## Rollback

## Journal

- 2026-05-01T10:47:10Z [implementation] — AC verified: 1. ✓ resolve_context_tier + DEFAULT в project_config; bootstrap валидирует перед bootstrap_ide; save_tausik_config setdefault. 2. ✓ EN/RU quickstart + build_full_body tiers. 3. ✓ Negative: ValueError при неверном tier; build_full_body игнорит мусор строку. Tests: AC-3: ✓ tested via tests/test_context_tier.py.
