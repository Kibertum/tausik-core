---
slug: fix-doc-count-drift
title: "Doc-count drift: устаревшие MCP/schema/table-числа врут агенту + дыра в сканере"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: "docs/ru/agent-contract.md, docs/ru/architecture.md, docs/en/architecture.md, docs/ru/senar-compliance-matrix.md, docs/en/senar-compliance-matrix.md, docs/README.md, README.md (числа); scripts/doc_drift_scanners.py (MCP_COUNT_EXTRA_TARGETS + scan_mcp_tool_counts). НЕ трогать: docs/audit/* (исторические снапшоты), constants.json (auto-gen), формулировки claims вне чисел."
scope_exclude: "docs/audit/**, docs/_generated/constants.json, version/test scanner логику"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T00:09:16Z"
---

## Goal

Доки (agent-facing) заявляют устаревшие числа, которые агент читает как истину: MCP-инструменты 93/98/100/105 (факт 116 project + 7 brain = 123), Schema v27 (факт v37), 17 таблиц + 4 FTS5 (факт 27 + 8), 138 source-файлов. Cross-file drift-сканер покрывает только README/AGENTS/CLAUDE/architecture/mcp — agent-contract, senar-compliance-matrix, docs/README не проверяются, поэтому дрейф невидим. Исправить числа в живых доках (НЕ в historical docs/audit/*) и закрыть корневую причину: завести MCP_COUNT_EXTRA_TARGETS для MCP-count-сканера (без version-сканера, чтобы не ловить легитимные исторические v1.3/v1.4 refs).

## Acceptance Criteria

1. Все живые доки (agent-contract, architecture ru/en, compliance-matrix ru/en, docs/README) показывают MCP = 116 project + 7 brain = 123 (нет 93/98/100/105). 2. Schema v27 → v37 в architecture ru/en:120; таблицы '17+4 FTS5' → '27 tables + 8 FTS5' в architecture ru/en. 3. Volatile source-file число (138) убрано как точное число (рефраза без счётчика — устраняет класс дрейфа). 4. docs/audit/* НЕ изменены (исторические). 5. Корневая причина: MCP_COUNT_EXTRA_TARGETS добавлен, scan_mcp_tool_counts гоняется по CROSS_FILE_SCAN_TARGETS + extra; version/test-сканеры НЕ затрагивают extra-файлы. 6. Негативный сценарий: gen_doc_constants --check ловит искусственно внесённый неверный MCP-count в agent-contract (проверено: меняю число → --check выдаёт drift-сообщение с Ошибкой → возвращаю). 7. После фикса gen_doc_constants --check проходит чисто (exit 0, без drift). 8. test_gen_doc_constants и весь pytest зелёные, ruff чист.

## Plan

## Rollback

git revert/checkout затронутых .md и scripts/doc_drift_scanners.py — изменения чисто текстовые/аддитивные (новый кортеж targets + расширение цикла), без миграций и схемы. Откат не влияет на runtime CLI/MCP.

## Journal

- 2026-06-14T00:09:15Z [implementation] — AC-1: ✓ MCP=116 project+7 brain=123 во всех живых доках (agent-contract:119, architecture ru/en:104, compliance ru/en:80, docs/README:124, README:156, README.ru:156) — tested via grep sweep + gen_doc_constants --check CLEAN. AC-2: ✓ Schema v27→v37 (architecture ru/en:120), 17+4 FTS5→27+8 (ru/en:43,63). AC-3: ✓ volatile '138 source files' заменено на рефразу без числа. AC-4: ✓ docs/audit/* не тронуты (grep -v /audit/). AC-5: ✓ MCP_COUNT_EXTRA_TARGETS добавлен, scan_mcp_tool_counts гоняется по CROSS+extra, version/test-сканеры не затронуты — tested via tests/test_gen_doc_constants.py (46 passed). AC-6: ✓ Negative: инъекция '999 project' в agent-contract → --check выдал 'pair drift ... does not match' (Ошибка поймана), revert→clean. AC-7: ✓ gen_doc_constants --check exit 0 CLEAN. AC-8: ✓ pytest 46 passed, ruff clean. Domain: агент теперь читает правдивые числа.
