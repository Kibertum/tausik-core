---
slug: v14-docs-verify-glossary
title: "EN/RU глоссарий: opt-out vs bypass vs test shim"
status: done
epic: v14-verify-integrity
story: v14-verify-policy-docs
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "docs/en docs/ru"
scope_exclude: "docs/research scripts agents"
relevant_files:
  - "docs/en/verify-glossary.md"
  - "docs/ru/verify-glossary.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T10:13:55Z"
---

## Goal

Один источник правды для агентов и пользователей.

## Acceptance Criteria

1. Разделы в docs/en и docs/ru согласованы. 2. Чеклист ревью. 3. Negative: противоречивые определения помечены как TODO или исправлены.

## Plan

## Rollback

## Journal

- 2026-05-01T10:13:40Z [implementation] — AC1: docs/en/verify-glossary.md + docs/ru/verify-glossary.md (mirrored tables, opt-out/bypass/shim). AC2: doc review checklist в обоих. AC3: согласованы формулировки cache bypass vs QG bypass; перекрёстные ссылки README, cli, mcp.
- 2026-05-01T10:13:47Z [implementation] — AC verified: 1. ✓ EN/RU разделы согласованы (verify-glossary.md). 2. ✓ Чеклист ревью в обоих файлах. 3. ✓ Противоречий нет: QG bypass vs verify-cache bypass и opt-out разведены явно.
