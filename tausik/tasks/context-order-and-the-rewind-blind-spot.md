---
slug: context-order-and-the-rewind-blind-spot
title: "Порядок инъекции контекста под кэш и слепое пятно /rewind нигде не записаны"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-knowledge-lifecycle
complexity: simple
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#143"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ДВА ФАКТА ИЗ РАЗБОРА ЧУЖИХ РЕШЕНИЙ (#189), КОТОРЫЕ У НАС НЕ ЗАПИСАНЫ НИГДЕ И СТОЯТ НОЛЬ.
1. ПОРЯДОК ИНЪЕКЦИИ ПОД КЭШ. В архитектуре Managed Agents харнесс организует контекст РАДИ попадания в кэш промпта. У нас блок памяти впрыскивается на старте и меняется каждый раз — то есть ломает стабильный префикс и обнуляет выгоду кэша для всего, что стоит после него. Правило: стабильное (CLAUDE.md, контракт, ядро памяти) — раньше, изменчивое (хвост журнала, статус, выбранные по релевантности записи) — позже.
2. `/rewind` НАМ НЕ СТРАХОВКА. Чекпойнты Claude Code отслеживают только правки его собственными файловыми инструментами; правки через Bash и внешние процессы в снимок НЕ ПОПАДАЮТ. Мы работаем в bypass-режиме и почти всё делаем Bash'ем, значит наша единственная сеть — git. Это обязано быть сказано прямо, иначе следующий агент понадеется на откат, которого нет.
ЧТО ДЕЛАЕТСЯ: обе вещи записываются в CLAUDE.md и docs/{ru,en}, а порядок инъекции проверяется тестом, а не глазами.

## Acceptance Criteria

## Plan

## Rollback

Правка документации плюс один тест на порядок сборки блока. Откат — git revert.

## Journal
