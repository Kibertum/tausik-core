---
slug: skill-profile-variants-structure-two-independent-axes
task: b8-pre-model-profile-auto-detect-interactive-promp
date: "2026-05-07"
edges: []
---

## Decision

Skill profile variants/ structure: two independent axes — variants/ide/{slug}.md + variants/model/{slug}.md. Two-pass merge: base + ide + model overlay. Backward compat with legacy flat variants/{slug}.md retained.

## Rationale

Cursor IDE может крутить и Claude и GPT — IDE и модель нужно резолвить независимо. Decoupled axes избегают N×M-комбинаторики плоского cursor-gpt-5.md, держат DRY (один model/gpt-5.md работает для всех IDE), упрощают добавление новых моделей/IDE. Disk pre-merge при cache miss + sha256 идемпотентность держат runtime cost = 0 на cache hit. Решение принято в Q1 ответе пользователю; реализовано в b8-pre-model-profile-auto-detect.
