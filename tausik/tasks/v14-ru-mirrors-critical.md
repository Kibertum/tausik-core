---
slug: v14-ru-mirrors-critical
title: "RU mirrors: 4 критических EN доков (permissions, security-checklist, model-providers, brain-search-ranking)"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T09:36:46Z"
---

## Goal

4 EN docs не имеют RU зеркал и пользователь явно попросил перевести их сейчас. Создать docs/ru/ зеркала с идентичной структурой (headers, code blocks, links). После — обновить docs/README.md RU секцию.

## Acceptance Criteria

1. docs/ru/permissions.md создан как зеркало docs/en/permissions.md.
2. docs/ru/security-checklist.md создан как зеркало docs/en/security-checklist.md.
3. docs/ru/model-providers.md создан как зеркало docs/en/model-providers.md.
4. docs/ru/brain-search-ranking.md создан как зеркало docs/en/brain-search-ranking.md.
5. Структура (headers, code blocks, links) идентична источнику.
6. docs/README.md (RU section) обновлён — 4 новых entry в правильных категориях.
7. Negative: docs/en/* не тронуты.
relevant_files: docs/ru/permissions.md, docs/ru/security-checklist.md, docs/ru/model-providers.md, docs/ru/brain-search-ranking.md, docs/README.md

## Plan

## Rollback

## Journal

- 2026-05-03T09:36:46Z [implementation] — AC verified: 1. ✓ docs/ru/permissions.md (134 lines parity). 2. ✓ docs/ru/security-checklist.md (82 lines parity). 3. ✓ docs/ru/model-providers.md (37 lines parity). 4. ✓ docs/ru/brain-search-ranking.md (12 lines parity, переписан по EN source). 5. ✓ Структура (headers, code blocks, links) идентична — все 4 субагента подтвердили line-by-line parity. 6. ✓ docs/README.md RU section: permissions, model-providers, brain-search-ranking уже были в обновлённом index; security-checklist добавлен в Безопасность секцию. 7. ✓ Negative: docs/en/* не тронуты subagents.
