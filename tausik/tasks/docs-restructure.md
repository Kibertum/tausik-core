---
slug: docs-restructure
title: "Реструктуризация docs: ru/en поддиректории, English-first README"
status: done
epic: null
story: null
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
  - "docs/README.md"
  - "docs/en/"
  - "docs/ru/"
  - "docs/dev/i18n-strategy.md"
  - "docs/dev/vendor-skills.md"
  - "docs/dev/senar-compliance-matrix.md"
  - "references/QUICKSTART.md"
  - "references/QUICKSTART.en.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-06T10:40:06Z"
---

## Goal

Чистая структура docs/ru + docs/en + docs/dev. README.md = English, README.ru.md = Russian. Все ссылки обновлены. Дубли из references удалены.

## Acceptance Criteria

1. README.md = English, README.ru.md = Russian с language switcher. 2. docs/en/ содержит 7 файлов (quickstart, workflow, skills, hooks, cli, mcp, architecture). 3. docs/ru/ содержит те же 7 файлов. 4. docs/dev/ содержит adding-new-ide, vendor-skills, i18n-strategy, senar-compliance-matrix. 5. references/ не содержит getting-started.md, skills-guide.md, mcp-reference.md, roles/, stacks/. 6. Все внутренние ссылки в docs обновлены. 7. CLAUDE.md ссылки на references/ актуальны. 8. Ошибка если docs/*.md файлы лежат в корне docs/ (кроме README.md).

## Plan

## Rollback

## Journal

- 2026-04-06T10:40:04Z [implementation] — Done. README.md=EN, README.ru.md=RU. docs/en/ (8 files), docs/ru/ (8 files), docs/dev/ (3 files). Removed duplicates from references/. All internal links updated. i18n-strategy.md rewritten. 751 tests pass.
