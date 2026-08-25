---
slug: graph-mermaid-render
title: "Diagram-as-code: mermaid-рендер графов TAUSIK (memory-graph, epic→story→task, RENAR) — заимствование cubest"
status: done
epic: landscape-2026-h2
story: borrow-cubest-onyx
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "Новый scripts/graph_mermaid.py + подключение в scripts/project_cli_ops.py или project_cli (memory graph / roadmap) + tests/test_graph_mermaid.py"
scope_exclude: "Изменение схемы графа/данных; интерактивные дашборды (ECharts из cubest — отложено); другие форматы (dot/plantuml) кроме mermaid — при необходимости отдельной задачей"
relevant_files:
  - "scripts/graph_mermaid.py"
  - "tests/test_graph_mermaid.py"
scope_paths:
  - "scripts/graph_mermaid.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_parser.py"
  - "tests/test_graph_mermaid.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-26T08:24:58Z"
---

## Goal

Дать агенту и человеку diagram-as-code представление структур TAUSIK (по образцу cubest, рендерящего куб в mermaid/dot): граф памяти (memory_edges), иерархия epic→story→task, RENAR-трасса. Один рендерер БД→mermaid, подключённый к существующим командам (memory graph, roadmap) через флаг --format mermaid. Детерминированный вывод (стабильный порядок узлов/рёбер — как в state-export). Вписывается в artifact-паттерн (mermaid рендерится нативно в артефактах).

## Acceptance Criteria

1. Рендерер БД→mermaid для ≥1 графа (memory_edges обязательно); ДЕТЕРМИНИРОВАННЫЙ порядок узлов и рёбер (как state-export: узлы по слагу, рёбра по кортежу). 2. Подключено к команде через --format mermaid (memory graph и/или roadmap). 3. Валидный mermaid-синтаксис (парсится рендерером; спецсимволы в лейблах экранируются). 4. НЕГАТИВ: пустой граф → валидный пустой mermaid (не падение, не мусорный вывод); лейбл со спецсимволами (кавычки, стрелки, переводы строк) экранируется и не ломает диаграмму. 5. ДЕТЕРМИНИЗМ: два прогона на одном стейте дают идентичный вывод байт-в-байт. 6. Полный scoped verify зелёный.

## Plan

## Rollback

Чистое дополнительное представление (--format mermaid), прежние форматы не тронуты. Откат: git revert коммита. Не меняет данные/схему.

## Journal

- 2026-07-26T08:24:56Z [implementation] — AC verified: 1. ✓ Рендерер БД→mermaid для memory_edges, детерминированный порядок (узлы sorted id, рёбра sorted (source,relation,target)): test_graph_mermaid.py::test_render_has_header_nodes_and_sorted_edges; живой прогон на реальной БД дал валидный mermaid 2. ✓ Подключено через --format mermaid к memory graph: parser парсит (проверено build_parser), cmd_memory graph рендерит; живой `tausik memory graph --format mermaid` выдал flowchart 3. ✓ Валидный mermaid, лейблы экранированы: ::test_label_sanitises_mermaid_breaking_chars ([]|"<> и newline не выживают), node_id санитизирует дефисы/цифру-в-начале (::test_node_id_sanitises_hyphens_and_digit_start) 4. ✓ НЕГАТИВ: пустой граф → валидный 'graph LR\n' (::test_empty_graph_is_valid_empty_mermaid); dangling edge → skip без краха (::test_dangling_edge_skipped_not_crash); спецсимволы/кириллица экранированы (живой прогон) 5. ✓ ДЕТЕРМИНИЗМ: два прогона идентичны (::test_render_is_deterministic); archived память исключена (::test_archived_memory_excluded), изолированные узлы опущены (::test_only_edge_participating_nodes_included) 6. ✓ Scoped verify PASS (pytest test_graph_mermaid — 8 тестов); 373 memory/graph регрессионных зелёные; ruff чист; filesize под cap (graph_mermaid 94, parser 398); bootstrap redeploy; changelog с атрибуцией cubest (конвенция #312)
- 2026-07-26T08:28:29Z [done] — Domain: на ЖИВОЙ БД `tausik memory graph --format mermaid` выдал валидный flowchart — узлы с кириллическими заголовками корректно экранированы и обрезаны (…), рёбра supersedes/relates_to отрендерены, node-id санитизированы (m_/d_ + underscore). Вывод семантически валиден как Mermaid вне юнит-тестов (парсится нативно в артефактах/GitHub/Obsidian). Заимствование cubest задокументировано в changelog (конвенция #312).
