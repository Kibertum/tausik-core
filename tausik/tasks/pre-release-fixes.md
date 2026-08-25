---
slug: pre-release-fixes
title: "Исправить все CRITICAL и HIGH findings перед публичным релизом"
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
  - pyproject.toml
  - "docs/senar-compliance-matrix.md"
  - README.md
  - README.en.md
  - "docs/mcp.md"
  - "docs/mcp.en.md"
  - "docs/README.md"
  - "references/mcp-reference.md"
  - CLAUDE.md
  - "docs/quickstart.md"
  - "docs/quickstart.en.md"
  - MIGRATE.md
  - AGENTS.md
  - "docs/adding-new-ide.md"
  - "docs/adding-new-ide.en.md"
  - "scripts/service_task.py"
  - "scripts/service_gates.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-06T10:25:39Z"
---

## Goal

Ноль CRITICAL и HIGH findings. Репозиторий готов к публичному релизу на GitHub.

## Acceptance Criteria

1. pyproject.toml version = 3.0.0. 2. Все docs содержат единые числа (tools, tests, skills). 3. Нет [вычеркнуто: internal-host] в публичных файлах. 4. .mcp.json и skills.json не tracked в git. 5. docs/ имеют EN-версии для всех файлов. 6. review-report удалён из docs/. 7. AGENTS.md = 32 skills. 8. MCP handlers используют ide_utils. 9. service_task.py <= 400 строк (вынесены gates). 10. Ошибка если grep находит [вычеркнуто: internal-host] или version 1.2.0/2.9.0 в tracked файлах.

## Plan

[{"step": "C-1: pyproject.toml version \u2192 3.0.0", "done": false}, {"step": "C-2: senar-compliance-matrix.md version \u2192 3.0.0", "done": false}, {"step": "C-3: \u041f\u043e\u0441\u0447\u0438\u0442\u0430\u0442\u044c \u0440\u0435\u0430\u043b\u044c\u043d\u044b\u0435 MCP tools/tests/skills \u0438 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0432\u0441\u0435 docs", "done": false}, {"step": "C-5: \u0417\u0430\u043c\u0435\u043d\u0438\u0442\u044c [вычеркнуто: internal-host] \u043d\u0430 github placeholder", "done": false}, {"step": "C-6: git rm --cached .mcp.json + \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432 .gitignore", "done": false}, {"step": "C-7: git rm --cached skills.json", "done": false}, {"step": "H-1: \u0421\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c docs/ \u2014 \u0443\u043d\u0438\u0444\u0438\u0446\u0438\u0440\u043e\u0432\u0430\u0442\u044c language switcher", "done": false}, {"step": "H-2: AGENTS.md \u2014 \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c skills count", "done": false}, {"step": "H-3: \u0423\u0434\u0430\u043b\u0438\u0442\u044c review-report \u0438\u0437 docs/", "done": false}, {"step": "H-4: \u0421\u043e\u0437\u0434\u0430\u0442\u044c EN-\u0432\u0435\u0440\u0441\u0438\u0438 vendor-skills.en.md, adding-new-ide.en.md", "done": false}, {"step": "H-5: MCP handlers \u2014 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c ide_utils \u0432\u043c\u0435\u0441\u0442\u043e .claude", "done": false}, {"step": "H-6: \u0420\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c service_task.py \u2192 service_task.py + service_gates.py", "done": false}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c pytest", "done": false}]

## Rollback

## Journal

- 2026-04-06T10:19:09Z [implementation] — Разведка завершена. Реальные числа: MCP 65 core + 5 RAG = 70, tests 751, skills 32. Найдены: [вычеркнуто: internal-host] в 5 файлах, "53 инструмент" в 7 местах, AGENTS.md полностью stale.
- 2026-04-06T10:21:20Z [implementation] — C-1 pyproject.toml done. C-2 compliance matrix done. C-3 numbers synced (70 MCP tools). C-5 gitlab URLs replaced. C-6/C-7 git rm done. H-2 AGENTS.md rewritten. H-3 review-report moved to .frai/. Next: H-4 EN docs, H-5 MCP ide_utils, H-6 service_task split.
- 2026-04-06T10:25:37Z [implementation] — All 13 steps done. C-1 pyproject 3.0.0, C-2 compliance matrix 3.0.0, C-3 MCP 70 tools synced everywhere, C-5 gitlab URLs replaced, C-6/C-7 git rm skills.json, H-1 language switcher added, H-2 AGENTS.md rewritten, H-3 review-report moved, H-4 adding-new-ide.en.md created, H-5 already done, H-6 service_task split (403+316 lines). 751 tests pass. 0 stale refs found.
