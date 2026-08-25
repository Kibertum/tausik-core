---
slug: brainh-audit
title: "[P0-first] Brain pain-point аудит → improvement spec"
status: planning
epic: shared-knowledge
story: kb-notion
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Перед улучшениями — аудит tausik-brain: латентность Notion API, доля промахов brain_search, актуальность local index, лимиты/ошибки за историю использования, UX-фрикции (когда агент НЕ зовёт brain). Выход — короткая спека улучшений с приоритетами, уточняющая остальные задачи эпика. AC: документ docs/research/ с метриками и топ-5 болей; задачи эпика откорректированы по результатам.

## Acceptance Criteria

1. В docs/research/ создан документ аудита tausik-brain с измеренными метриками: латентность Notion API, доля промахов brain_search, актуальность локального индекса, история лимитов/ошибок использования.
2. В документе выписан топ-5 болей с приоритетами и UX-фрикции — конкретные сценарии, когда агент НЕ зовёт brain.
3. Задачи эпика откорректированы по результатам аудита: правки видны в их goal/AC со ссылкой на документ.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal
