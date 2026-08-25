---
slug: kb-docs-consistency
title: "Сквозная согласованность документации и doc-drift гейты"
status: planning
epic: shared-knowledge
story: kb-docs
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - docs
  - "scripts/gen_doc_constants.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ПОСЛЕ роя: один проход, который рой сделать не может по определению — сквозная проверка. Убедиться, что сквозные утверждения из карты звучат одинаково во всех документах и на обоих языках, что нет осиротевших упоминаний Notion как обязательного шага, что примеры команд соответствуют реальному CLI, что счётчики в constants.json и бейджи README пересчитаны, а строгий doc-check зелёный. Отдельно проверить, что doc-drift сканеры не пропускают новые сущности: общая база, выгрузка, публикатор.

## Acceptance Criteria

1. Сквозные утверждения из карты звучат одинаково во всех документах и на ОБОИХ языках.
2. Не осталось осиротевших упоминаний Notion как ОБЯЗАТЕЛЬНОГО шага; примеры команд соответствуют реальному CLI.
3. Счётчики в constants.json и бейджи README пересчитаны; строгий doc-check зелёный.
4. Doc-drift сканеры покрывают новые сущности (общая база, выгрузка, публикатор) и не пропускают их.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; проверки согласованности снимаются

## Journal
