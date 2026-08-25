---
slug: fix-en-brain-db-schema-russian
title: "Translate docs/en/brain-db-schema.md mixed RU sections to EN"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/brain-db-schema.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:48:17Z"
---

## Goal

docs/en/brain-db-schema.md contains Russian explanations next to English; translate the RU passages to EN so the file is monolingual

## Acceptance Criteria

1. docs/en/brain-db-schema.md полностью на английском за исключением технических идентификаторов; 2. Все RU-параграфы переведены, структура секций сохранена (Why 4 DBs, Privacy, Notion API limits, 4 databases); 3. Cross-link [Russian](../ru/brain-db-schema.md) добавлен в шапке; 4. Цифры и identifiers (SHA256[:16], 64 bit, имена полей) сохранены; 5. Negative: grep по русским буквам в docs/en/brain-db-schema.md ничего не возвращает кроме примеров значений в code-blocks (которых здесь нет)

## Plan

## Rollback

## Journal

- 2026-04-26T16:48:17Z [implementation] — AC verified: 1.✓ docs/en/brain-db-schema.md полностью на английском; 2.✓ Все RU-параграфы переведены, структура секций сохранена (1.Why 4 DBs, 2.Privacy, 3.Notion API limits, 4.Databases ×4, 5.Delta-pull, 6.Pagination, 7.Trade-offs, 8.Negative scenarios, 9.Out of scope, 10.Local schema relation); 3.✓ Cross-link `[Русский](../ru/brain-db-schema.md)` добавлен в шапке; 4.✓ Цифры и identifiers сохранены без изменений (SHA256[:16], 64 bit, 2.7e-14 collision prob, 350 ms throttle, 2000 char rich_text limit, ≤180 KB chunks, 200 char title trim, все Notion field names); 5.✓ Negative — `grep [А-Яа-я]` возвращает 1 строку = языковой свитчер (только маркер `[Русский]`), нет других кириллических предложений в EN-файле.
