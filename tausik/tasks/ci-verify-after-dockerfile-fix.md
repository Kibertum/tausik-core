---
slug: ci-verify-after-dockerfile-fix
title: "CI verify after Dockerfile fix"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T13:58:01Z"
---

## Goal

Push Dockerfile fix и подтвердить что CI прошёл

## Acceptance Criteria

(1) Pipeline на новом commit показывает status=success. (2) Build + deploy stages зелёные. (3) Live tausik.tech подхватывает новый контент. (4) Ошибка: если build снова падает — нужен retry/iteration.

## Plan

## Rollback

## Journal

- 2026-05-15T13:58:01Z [implementation] — AC verified: Pipeline #2277 (a7aa6d4) — success. Build 18s + deploy 6s, обе stages зелёные. Dockerfile fix подхватил docs/_generated/constants.json, vite build разрезолвил import. Live tausik.tech теперь содержит весь накопленный контент: NOT-section, comparison table, FAQ, числа из constants, hero lede, 12 orphan-страниц в sidebar, все 12 doc-defect fixes.
