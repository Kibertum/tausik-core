---
slug: port-external-pr5-hook-coverage
title: "Перенести внешний PR #5 (покрытие хуков) в основной репозиторий: часть уже сделана в 1.8, часть нет"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: complex
role: backend
stack: null
tier: substantial
call_budget: 90
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/hooks/*.py"
  - "bootstrap/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
completed_at: null
---

## Goal

Каждое утверждение PR #5 проверено против дерева 1.8 и либо перенесено с тестом, либо закрыто как уже сделанное — с указанием, ЧЕМ именно.

## Acceptance Criteria

1. Составлена таблица «утверждение PR #5 -> состояние в 1.8»: что уже закрыто (PowerShell в матчерах, NotebookEdit в task_gate и scope_write_gate, shell_channel, mcp<2 в requirements) и что НЕТ.
2. Перенесено то, что нет: якорение матчеров ^(?:...)$, покрытие MCP-редакторов (serena, windows-mcp), MultiEdit в auto_format, NotebookEdit в memory_posttool_audit, единый источник имён инструментов в _common, поле пути в payload у каждого инструмента (file_path / notebook_path / path / relative_path / destination).
3. Каждая перенесённая правка приходит СО СВОИМ тестом, который на старом коде краснеет.
4. Автор PR #5 указан соавтором в коммите; PR закрыт ссылкой на перенос, а не молча.
5. НЕГАТИВНЫЙ сценарий: тест доказывает, что запись через инструмент, не попадавший в матчер, теперь БЛОКИРУЕТСЯ без активной задачи. Утверждение «хук отработал» не принимается за доказательство: хук, не увидевший вызова, тоже выходит с нулём, и отличить это можно только по факту блокировки.
6. НЕГАТИВНЫЙ сценарий: якорение матчеров не должно ОТКЛЮЧИТЬ ни один работающий сегодня перехват — до и после правки собирается список (инструмент, хук), и он только растёт.

## Plan

## Rollback

git revert коммита; ветка порта отдельная, в main вливается одним куском

## Journal
