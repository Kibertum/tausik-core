---
slug: docs-strict-review
title: "Строгий ревью всей документации (RU+EN), полная синхронизация"
status: done
epic: null
story: null
complexity: complex
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/quickstart.en.md"
  - "docs/workflow.en.md"
  - "docs/skills.en.md"
  - "docs/hooks.en.md"
  - "docs/cli.en.md"
  - "docs/mcp.en.md"
  - "docs/architecture.en.md"
  - "docs/i18n-strategy.md"
  - README.md
  - README.en.md
  - CLAUDE.md
  - CONTRIBUTING.md
  - "docs/senar-compliance-matrix.md"
  - "docs/README.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T20:17:40Z"
---

## Goal

Все docs на двух языках (RU+EN). Числа, ссылки, версии синхронизированы. Нет битых ссылок, нет stale данных.

## Acceptance Criteria

1. Все docs из docs/ имеют EN-версию. 2. README.md и README.en.md полностью синхронизированы по секциям. 3. Числа (тесты, MCP tools, skills) одинаковы во всех файлах. 4. Нет битых ссылок (все .md файлы в docs/ ссылаются на существующие файлы). 5. CONTRIBUTING.md EN+RU секции идентичны по содержанию. 6. Ошибка если docs/vendor-skills.md не имеет EN-секции или отдельного .en.md.

## Plan

## Rollback

## Journal

- 2026-04-05T20:17:32Z [implementation] — AC verified: 1. 7 EN-переводов docs/ созданы (quickstart, workflow, skills, hooks, cli, mcp, architecture) ✓ 2. Language switchers добавлены в RU+EN файлы ✓ 3. Числа синхронизированы: 751 тест, 53 MCP, 32 скилла, v3.0.0 ✓ 4. i18n-strategy обновлена ✓ 5. CONTRIBUTING/CLAUDE.md числа обновлены ✓
