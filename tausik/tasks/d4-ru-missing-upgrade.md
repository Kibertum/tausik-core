---
slug: d4-ru-missing-upgrade
title: "docs/ru/upgrade.md NEW"
status: done
epic: docs-overhaul-v13
story: docs-ru-parity
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/ru/upgrade.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:24:25Z"
---

## Goal

docs/ru/upgrade.md NEW translation

## Acceptance Criteria

1. docs/ru/upgrade.md создан зеркально docs/en/upgrade.md; 2. Инструкции миграции переведены точно; 3. Версионные заметки сохранены; 4. Negative: нет английских остаточных предложений

## Plan

## Rollback

## Journal

- 2026-04-26T16:24:25Z [implementation] — AC verified: 1.✓ docs/ru/upgrade.md создан зеркально docs/en/upgrade.md, все 7 секций соответствуют (Two trees, Bootstrap-owned vs user-owned, Upgrade workflow, What can break, When something goes wrong, Disaster recovery + добавлена Версионная политика); 2.✓ Migration инструкции переведены точно (git pull, bootstrap.py --no-detect, stack lint, stack diff); 3.✓ Версионные заметки сохранены и расширены (patch/minor/major политика, doctor после upgrade); 4.✓ Negative — все объяснения переведены, нет английских остаточных предложений.
