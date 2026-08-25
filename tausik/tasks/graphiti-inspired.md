---
slug: graphiti-inspired
title: "Графовая память — связи между записями (Graphiti-inspired)"
status: done
epic: null
story: null
complexity: null
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-23T21:39:04Z"
---

## Goal

Добавить графовый слой поверх плоской памяти: таблица memory_edges с soft-invalidation рёбер, CLI/MCP/Service для управления связями, автопоиск похожих записей

## Acceptance Criteria

1) Таблица memory_edges с soft-invalidation (valid_to, invalidated_by). 2) CLI: memory link/unlink/graph/related. 3) MCP инструменты для графа. 4) При memory add и decide — автопоиск и предложение связей. 5) Миграция v11. 6) FTS5 + CTE для обхода графа. 7) Тесты. 8) Документация (CHANGELOG, README, project-cli.md). 9) Никогда не удалять рёбра — только инвалидировать.

## Plan

[{"step": "1. Schema: memory_edges \u0442\u0430\u0431\u043b\u0438\u0446\u0430 + FTS5 + \u0442\u0440\u0438\u0433\u0433\u0435\u0440\u044b + \u0438\u043d\u0434\u0435\u043a\u0441\u044b \u0432 backend_schema.py", "done": true}, {"step": "2. Migration v11 \u0432 backend_migrations.py", "done": true}, {"step": "3. Backend CRUD: edge_add, edge_invalidate, edge_list, edge_related, edge_graph \u0432 project_backend.py", "done": true}, {"step": "4. Backend queries: graph traversal \u0447\u0435\u0440\u0435\u0437 \u0440\u0435\u043a\u0443\u0440\u0441\u0438\u0432\u043d\u044b\u0439 CTE \u0432 backend_queries.py", "done": true}, {"step": "5. Service layer: link, unlink, related, graph + \u0430\u0432\u0442\u043e\u043f\u043e\u0438\u0441\u043a \u043f\u0440\u0438 memory_add/decide \u0432 service_knowledge.py", "done": true}, {"step": "6. CLI: memory link/unlink/graph/related \u0432 project_parser.py + project_cli_extra.py", "done": true}, {"step": "7. MCP: frai_memory_link, frai_memory_unlink, frai_memory_related, frai_memory_graph \u0432 tools.py + handlers.py", "done": true}, {"step": "8. \u0422\u0435\u0441\u0442\u044b: unit (backend), service, CLI smoke, FTS sync, edge cases", "done": true}, {"step": "9. \u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u044f: project-cli.md, architecture.md, CHANGELOG.md, README.md", "done": true}, {"step": "10. \u0424\u0438\u043d\u0430\u043b\u044c\u043d\u0430\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430: pytest + ruff + smoke test CLI", "done": true}]

## Rollback

## Journal
