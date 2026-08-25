---
slug: v14-artifact-taxonomy
title: "Таксономия: artifact vs pattern vs snippet"
status: done
epic: v14-brain-snippets
story: v14-brain-snippets-model
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_artifact_taxonomy.py"
  - "scripts/brain_config.py"
  - "scripts/brain_mcp_write.py"
  - "scripts/service_verification.py"
  - "scripts/verify_recent_lookup.py"
  - "tests/test_brain_mcp_write.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T11:29:54Z"
---

## Goal

Зафиксировать типы карточек и поля классификации для Shared Brain.

## Acceptance Criteria

1. Документ или схема с определениями artifact/pattern/snippet. 2. Пример минимальной карточки. 3. Negative: запись без категории отклоняется или помечается invalid.

## Plan

## Rollback

## Journal

- 2026-05-01T11:24:32Z [implementation] — AC: (1) docs/en+ru/brain-artifact-taxonomy.md + shared-brain ссылки; (2) пример минимальной карточки JSON в доке; (3) strict require_artifact_taxonomy_kind блокирует store без kind; явный invalid kind блокируется; artifact_taxonomy_kind не уходит в Notion props — pytest tests/test_brain_mcp_write.py (45).
- 2026-05-01T11:24:44Z [implementation] — AC verified: 1. ✓ Документы en/ru brain-artifact-taxonomy + минимальный JSON-пример в доке + ссылки из shared-brain. 2. ✓ Карточка-пример как в доке. 3. ✓ Строгий режим блокирует отсутствие kind; невалидный kind блокируется; pytest test_brain_mcp_write taxonomy cases.
- 2026-05-01T11:27:45Z [implementation] — FIX: lookup_recent_for_task — поиск по (slug, hash, command), чтобы зелёный task-done не перекрывал кэш verify (verify-first QG-2).
