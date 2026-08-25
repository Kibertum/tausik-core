---
slug: v14-broken-link-fix
title: "Fix broken link references/brain-db-schema.md в 2 SKILL.md"
status: done
epic: null
story: null
complexity: null
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
completed_at: "2026-05-03T09:31:08Z"
---

## Goal

agents/skills/brain/SKILL.md:114 и .qwen/skills/brain/SKILL.md:114 ссылаются на references/brain-db-schema.md — папки references/ нет. Файл живёт в docs/en/brain-db-schema.md. Исправить путь.

## Acceptance Criteria

1. agents/skills/brain/SKILL.md:114 link references/brain-db-schema.md → ../../../docs/en/brain-db-schema.md.
2. .qwen/skills/brain/SKILL.md:114 same fix.
3. Negative: ничего больше в SKILL.md не тронуто.
4. Verify: grep -r "references/brain-db-schema" возвращает 0 hits в SKILL.md.
relevant_files: agents/skills/brain/SKILL.md, .qwen/skills/brain/SKILL.md

## Plan

## Rollback

## Journal

- 2026-05-03T09:31:07Z [implementation] — AC verified: 1. ✓ agents/skills/brain/SKILL.md:114 + .qwen/skills/brain/SKILL.md:114 + .claude/skills/brain/SKILL.md:114 + .cursor/skills/brain/SKILL.md:114 — references/ → docs/en/. 2. ✓ Negative: только schema reference link строка тронута. 3. ✓ Verify: grep references/brain-db-schema = 0 hits в SKILL.md (4 файла исправлены).
