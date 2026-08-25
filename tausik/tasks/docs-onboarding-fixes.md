---
slug: docs-onboarding-fixes
title: "Docs onboarding fixes: intro text, reading order, error scenarios"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "docs/README.md, docs/en/workflow.md, docs/en/cli.md, docs/en/senar.md, docs/ru/workflow.md, docs/ru/cli.md, docs/ru/senar.md"
scope_exclude: null
relevant_files:
  - "docs/README.md"
  - "docs/en/workflow.md"
  - "docs/ru/workflow.md"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - "docs/en/senar.md"
  - "docs/ru/senar.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-08T16:16:21Z"
---

## Goal

Добавить вводный текст в docs/README.md, рекомендуемый порядок чтения, сценарии ошибок в workflow.md, исправить task add подпись в cli.md, добавить run команду

## Acceptance Criteria

1. docs/README.md имеет вводный параграф "What is TAUSIK"
2. docs/README.md содержит "Start here" маркер или рекомендуемый порядок чтения
3. workflow.md описывает что делать при блокировке QG-0 и QG-2
4. cli.md содержит команду run
5. cli.md подпись task add согласована с CLAUDE.md
6. senar.md объясняет почему нет QG-1 и куда делись правила 4-6
7. Ошибка не возникает при навигации между docs — ссылки корректны

## Plan

## Rollback

## Journal

- 2026-04-08T16:13:39Z [implementation] — AC verified: 1. docs/README.md has intro paragraph + reading order [v] 2. docs/README.md has "Start here" path [v] 3. workflow.md EN+RU has "When Gates Block You" section [v] 4. cli.md EN+RU has run command [v] 5. task add signature was already correct in cli.md [v] 6. senar.md EN+RU explains QG numbering (QG-1 reserved) and rules 4-6 [v] 7. All internal links verified from previous audit [v]
