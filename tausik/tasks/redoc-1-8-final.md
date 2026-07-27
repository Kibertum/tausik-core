---
slug: redoc-1-8-final
title: "Итоговая редокументация фреймворка под релиз 1.8 (вся пользовательская документация ↔ код)"
status: planning
epic: null
story: null
complexity: complex
role: tech-writer
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: "docs/ru/*, docs/en/*, README.md, CHANGELOG*.md. ТОЛЬКО документация — код/схему/гейты НЕ трогать (если найдено расхождение, где код прав — завести отдельный баг-таск, не чинить здесь)."
scope_exclude: "Изменение кода/схемы/гейтов; borrow-фичи, ещё не влитые (документируются в своих задачах); генерация нового функционала"
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Финальный документационный проход перед релизом 1.8: привести ВСЮ пользовательскую документацию в соответствие с фактическим состоянием после 1.8. Охват: docs/ru + docs/en (architecture, quickstart, cli, agent-contract), README, CHANGELOG-консолидация. Что задокументировать: git-native round-trip (state export/import, tausik sync, lifecycle triggers, team-state-in-git), все НОВЫЕ CLI-команды и флаги, borrow-фичи по мере реализации (tool-output-rollup, rag-contextual-chunk-prefix, mcp-scope-tools-exposure, graph-mermaid-render), обновлённые гейты/конвенции/хуки. Сверить доки с кодом (doc-drift, doc constants --check, docs_lint), убрать устаревшее. Reconcile с kb-docs-swarm (использовать роевой механизм по зонам, если готов) — это ФИНАЛЬНЫЙ проход, а не дубль. Запустить в самом конце 1.8, когда все фичи влиты.

## Acceptance Criteria

1. Все новые команды 1.8 (tausik state export/import с флагами, tausik sync) задокументированы в docs/{en,ru}/cli.md с примерами. 2. Round-trip и эпик team-state-in-git описаны в architecture.md + quickstart.md (что едет в git, раскладка tausik/, sync после pull). 3. Borrow-фичи (rollup, contextual-prefix, mcp-scope-tools, mermaid) задокументированы по мере реализации — на момент запуска задачи покрыть все ВЛИТЫЕ. 4. doc-drift зелёный: tausik doc constants --check + docs_lint + drift провенанс без расхождений доки↔код. 5. НЕГАТИВ: нет ссылок на несуществующие команды/флаги/файлы — проверка автоматическим сканером (docs_lint stale-mention = 0 для затронутых доков). 6. README отражает 1.8 (headline-фича — командное состояние в git). 7. EN/RU синхронизированы (нет раздела, живущего только на одном языке). 8. CHANGELOG [Unreleased] консолидирован и готов к датированию релиза.

## Plan

## Rollback

Чистая документация. Откат: git revert коммита. Не трогает код/поведение, поэтому риск только косметический. doc-drift гейт ловит регрессию доков.

## Journal
