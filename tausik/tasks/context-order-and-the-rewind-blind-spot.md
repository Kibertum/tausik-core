---
slug: context-order-and-the-rewind-blind-spot
title: "Порядок инъекции контекста под кэш и слепое пятно /rewind нигде не записаны"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/known-limitations.md"
  - "docs/ru/known-limitations.md"
  - "tests/test_context_order.py"
  - "changelog.d/context-order-and-the-rewind-blind-spot.md"
scope_paths:
  - "docs/"
  - "tests/"
  - "changelog.d/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:03:33Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#143"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
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

AC-1 docs/{en,ru}/known-limitations.md declare: Claude Code /rewind restores only edits made by its own file tools; Bash and external-process edits are not in the snapshot, so git is the only safety net. AC-2 The same pages state the context order: stable rules first, the changing part (DYNAMIC block: state, memory tail) last. AC-3 A test fails if the generated rules file or this repo's CLAUDE.md puts anything static after the DYNAMIC block. AC-4 NEGATIVE: a body with a static section after DYNAMIC:END is caught by the same check (the check is not hollow).

## Plan

## Rollback

Правка документации плюс один тест на порядок сборки блока. Откат — git revert.

## Journal

- 2026-09-29T22:03:11Z [implementation] — AC-1: ✓ docs/en/known-limitations.md + docs/ru: '/rewind does not undo what the agent did through the shell' (3-line declared-gap form, convention #777). AC-2: ✓ same pages, 'The rules file keeps its changing part last'. AC-3: ✓ tests/test_context_order.py::test_the_generated_rules_file_ends_with_the_dynamic_block, ::test_this_repository_s_claude_md_ends_with_the_dynamic_block. AC-4 Negative: ✓ tests/test_context_order.py::test_a_static_section_after_the_block_is_caught. Not in CLAUDE.md: its static cap (4096B) has no room, and memory #649 says context-economy rules do not belong in the per-turn file.
