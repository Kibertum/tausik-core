---
slug: mcp-doc-adapt-sign-row-still-describes-withdrawn-dual-signature
title: "docs/{en,ru}/mcp.md: строка tausik_adapt_sign всё ещё описывает отозванную двойную подпись клиента"
status: planning
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: simple
role: tech-writer
stack: null
tier: trivial
call_budget: 10
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

Задача adapt-dual-signature-implements-a-withdrawn-norm обновила описание инструмента в tools_adapt.py и вводные абзацы секции ADAPT в docs/{en,ru}/mcp.md, но не саму строку таблицы для tausik_adapt_sign: docs/en/mcp.md:146 и docs/ru/mcp.md:143 всё ещё гласят "architect signs the body with the project's ed25519 key, client signs with name+timestamp; both roles ⇒ approved" — а client-роль в adapt_sign теперь ОТКАЗЫВАЕТСЯ (ADR-011). Обновить обе строки под фактическое поведение (adapt_sign отвергает role=client, называя причину и ACTZ); свериться с tools_adapt.py как источником истины (правило "нет второй копии"). Найдено побочно при работе над actz-the-contract-contour-artifact-is-missing (правило "чужой дефект не поглощать").

## Acceptance Criteria

## Plan

## Rollback

## Journal
