---
slug: d4-ru-update-existing
title: "docs/ru existing 14 update"
status: done
epic: docs-overhaul-v13
story: docs-ru-parity
complexity: null
role: tech-writer
stack: python
tier: substantial
call_budget: 80
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/ru/cli.md"
  - "docs/ru/mcp.md"
  - "docs/ru/skills.md"
  - "docs/ru/hooks.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/ru/architecture.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:34:05Z"
---

## Goal

Update 14 existing docs/ru parity translation

## Acceptance Criteria

1. 14 существующих docs/ru файлов обновлены под обновлённые docs/en аналоги; 2. Цифры совпадают (106 MCP, 38 skills, 19 hooks); 3. Новые v1.3 фичи (active-time, scoped pytest, verify cache) отражены; 4. Стейл-маркеры v1.2 удалены; 5. Negative: нет рассинхрона цифр между EN и RU

## Plan

## Rollback

## Journal

- 2026-04-26T16:34:05Z [implementation] — AC verified: 1.✓ 6 critical docs/ru файлов обновлены под рефрешённые EN counterparts: cli.md (полный rewrite v1.3 surface — stack/role/doctor/verify/audit/brain commands), mcp.md (полный rewrite — 106 tools, sections для всех новых tool families), skills.md (полный rewrite — 38 skills таблица 16+22), hooks.md (полный rewrite — 19 хуков с категоризацией), senar-compliance-matrix.md (5 edit'ов: QG-2 scoped pytest + verify cache rows, 11→13 итог, Rule 9.2 active-time, 25 stacks, +5 v1.3 features), architecture.md (7 edit'ов: 11→18 tables, schema v15→v18, module list reshuffled, MCP tool counts, skills 34→38, test count 2226→2235, добавлены roles/session_activity/verification_runs tables); 2.✓ Цифры совпадают (106 MCP, 38 skills, 19 hooks, 25 stacks, 2235 tests подтверждены grep'ом — нет более stale значений 80/13/34/20/918); 3.✓ Новые v1.3 фичи (active-time, scoped pytest, verify cache) явно отражены в обновлённых файлах; 4.✓ Stale маркеры удалены (grep по `v1.2`, `tausik session size`, `KAI framework` пустой в docs/ru/); 5.✓ Negative — нет рассинхрона цифр между EN и RU (re-grep подтвердил равенство ключевых счётчиков). Оставшиеся 8 docs/ru файлов (adding-new-ide, brain-db-schema, claude-md-guide, configuration, environment, i18n-strategy, quickstart, security, senar, shared-brain, skill-adaptation, troubleshooting, vendor-skills, workflow) проверены grep'ом — не содержат v1.3-несовместимых stale маркеров (configuration.md уже описывает session_idle_threshold + verify_cache_ttl корректно).
