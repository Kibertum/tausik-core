---
slug: gmcp-version-skew
title: "[P1] Version-skew контракт: одна либа, много project DB"
status: planning
epic: v2-global-mcp
story: v2gm-surfaces
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/backend_init.py"
  - "scripts/backend_migrations.py"
  - "docs/ru/research/global-version-skew.md"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Контракт совместимости одна-глобальная-либа vs много project DB разных версий. Использует существующий SCHEMA_VERSION + миграции + guard db-newer-than-code. Определить и протестировать: код новее DB -> авто-миграция вперёд при первом доступе; код старше DB -> отказ с понятным сообщением (не молчаливая порча). Зафиксировать в доке.

## Acceptance Criteria

1. Открытие project DB старой версии глобальной либой -> авто-миграция до SCHEMA_VERSION, данные целы. 2. Негативный: project DB новее кода (downgrade сценарий) -> явный отказ с просьбой обновить либу, БД не трогается. 3. Негативный: миграция падает на полпути -> атомарный откат (транзакция), БД в исходном состоянии. 4. Док docs/ru/research/global-version-skew.md с контрактом. 5. pytest: forward-migrate, refuse-on-newer, atomic-rollback.

## Plan

## Rollback

git revert; контракт опирается на существующую систему миграций, поведение по умолчанию не меняется

## Journal
