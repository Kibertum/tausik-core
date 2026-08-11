---
slug: bookmark-corpus-review-what-to-take-and-into-which-release
title: "Разбор корпуса закладок владельца: что из чужой обвязки взять в TAUSIK и в какую версию"
status: active
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: "scripts/**, bootstrap/**, tests/** — это разбор, а не реализация; из него заводятся отдельные задачи"
relevant_files: []
scope_paths:
  - "docs/ru/research/*.md"
  - "docs/en/research/*.md"
scope_tools: []
completed_at: null
---

## Goal

Из 284 закладок владельца по обвязке AI-агентов выделены настоящие пробелы TAUSIK, а не пересказ чужих README, и разложены по версиям с ценой и риском.

## Acceptance Criteria

1. Разобраны ВСЕ 284 записи корпуса, а не выборка: срезы A-memory, B-harness, C-standards, D-security, E-other покрыты полностью.
2. Каждая находка названа с тем, что у TAUSIK ЕСТЬ сегодня по этой теме, — иначе это пересказ чужого README, а не находка.
3. Находки разложены по версиям (1.9 / 2.0 / исследование) с ценой и риском.
4. НЕГАТИВНЫЙ сценарий: находка, дублирующая существующую возможность TAUSIK, ОТБРАСЫВАЕТСЯ явно, с указанием, чем она дублируется. Список «двадцать идей», где половина уже сделана, считается провалом разбора.
5. НЕГАТИВНЫЙ сценарий: числа из LLM-сводок Sortula НЕ принимаются на веру — звёзды, даты и заявления о бенчмарках проверяются по источнику, прежде чем попасть в план.

## Plan

## Rollback

Артефакт разбора лежит в scratchpad; задачи из него заводятся отдельно и откатываются по одной

## Journal
