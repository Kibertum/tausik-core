---
slug: fix-en-claude-md-guide-russian
title: "Translate docs/en/claude-md-guide.md from RU to EN"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 12
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/claude-md-guide.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:46:05Z"
---

## Goal

docs/en/claude-md-guide.md is currently entirely in Russian; translate to English so the EN docs branch is consistent

## Acceptance Criteria

1. docs/en/claude-md-guide.md полностью на английском; 2. Структура (Golden Rules / Recommended Structure / Don't include / Do include / Maintenance) сохранена; 3. Code blocks с примерами CLAUDE.md content переведены на EN тоже (включая ХОРОШО/ПЛОХО → GOOD/BAD); 4. Cross-link на docs/ru/claude-md-guide.md (Russian original) добавлен в шапке; 5. Negative: после grep'а нет кириллических предложений в docs/en/claude-md-guide.md (только code-block strings допустимы как примеры из чужих кодбаз — но в этом файле их нет)

## Plan

## Rollback

## Journal

- 2026-04-26T16:46:05Z [implementation] — AC verified: 1.✓ docs/en/claude-md-guide.md полностью на английском (`grep [А-Яа-я]` возвращает только language switcher `[Русский]`); 2.✓ Структура сохранена (Golden Rules / Recommended Structure / What NOT/Do include / Maintenance) + расширена секцией Negative — Common Anti-Patterns; 3.✓ Code blocks ХОРОШО/ПЛОХО переведены на GOOD/BAD (5 примеров); 4.✓ Cross-link `[Русский](../ru/claude-md-guide.md)` добавлен в шапке; 5.✓ Negative — grep по кириллице возвращает 1 строку = языковой свитчер, нет других русских предложений в EN-файле.
