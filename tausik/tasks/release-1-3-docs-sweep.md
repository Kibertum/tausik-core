---
slug: release-1-3-docs-sweep
title: "Release docs sweep: version 1.3.x + EN/RU changelog and docs consistency"
status: done
epic: null
story: null
complexity: complex
role: null
stack: null
tier: substantial
call_budget: 150
defect_of: null
scope: "VERSION files, CHANGELOG.md, CHANGELOG.ru.md, README*.md, docs/en/*.md, docs/ru/*.md, scripts/* where version is declared"
scope_exclude: "Изменение бизнес-логики сервисов вне документационного контекста"
relevant_files:
  - "scripts/tausik_version.py"
  - pyproject.toml
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/README.md"
  - "docs/en/hooks.md"
  - "docs/ru/hooks.md"
  - CLAUDE.md
  - AGENTS.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-29T19:10:01Z"
---

## Goal

Обновить версию в линейке 1.3, оформить изменения в двух changelog (EN/RU), и привести документацию к консистентному состоянию по IDE/MCP/tested matrix

## Acceptance Criteria

1. Версия фреймворка обновлена в коде в пределах 1.3.x и отображается в статусе/доках. 2. CHANGELOG.md и CHANGELOG.ru.md содержат синхронные записи о новых изменениях (task_done_v2, cursor mcp project config, tested IDE matrix). 3. README.md и README.ru.md согласованы с changelog по supported/tested IDE. 4. docs/en и docs/ru ключевые страницы (quickstart, mcp, hooks, docs index) приведены к консистентной формулировке по MCP config locations и tested matrix. 5. Negative scenario: если не удаётся подтвердить факт для конкретной IDE/фичи, документация явно помечает это как expected/partial или needs verification, без ложного утверждения полного покрытия.

## Plan

## Rollback

## Journal

- 2026-04-29T19:06:49Z [implementation] — Старт: выполняю релизный docs sweep с bump версии 1.3.x, синхронизацией EN/RU changelog и выравниванием ключевой документации по tested IDE/MCP.
- 2026-04-29T19:09:51Z [implementation] — AC verified: 1. ✓ Version bumped to 1.3.7 in scripts/tausik_version.py and pyproject.toml (plus dynamic CLAUDE.md block). 2. ✓ CHANGELOG.md and CHANGELOG.ru.md updated with synced 1.3.7 release entry. 3. ✓ README.md and README.ru.md aligned with tested IDE matrix and refreshed metrics/test counters. 4. ✓ docs sweep done on key EN/RU pages: docs/README.md, docs/en/hooks.md, docs/ru/hooks.md, quickstart+mcp already aligned from prior patch. 5. ✓ Negative scenario policy kept explicit: expected/partial/needs-verification wording retained where full proof absent. Verification: python scripts/docs_lint.py => clean; pytest tests/test_project_mcp.py tests/test_mcp_integration.py tests/test_bootstrap_generate_mcp.py -q => 56 passed.
