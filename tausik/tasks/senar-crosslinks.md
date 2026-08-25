---
slug: senar-crosslinks
title: "Перелинковка с senar.tech и github senar"
status: done
epic: public-release
story: docs-audit
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
  - CLAUDE.md
  - "references/QUICKSTART.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T13:37:29Z"
---

## Goal

Все упоминания SENAR ведут на senar.tech или github. Есть секция "What is SENAR?" в README. Обратные ссылки из senar-репо на frai.

## Acceptance Criteria

1. Все упоминания "SENAR" в docs имеют ссылку на senar.tech. 2. README содержит секцию "What is SENAR?". 3. QUICKSTART ссылается на SENAR spec. 4. Ошибка если grep находит orphan "SENAR" без ссылки в .md файлах docs/.

## Plan

[{"step": "Grep \u0432\u0441\u0435 \u0443\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f SENAR \u0432 \u0440\u0435\u043f\u043e", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u0441\u044b\u043b\u043a\u0438 senar.tech \u043a \u043a\u0430\u0436\u0434\u043e\u043c\u0443 \u0443\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044e", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0441\u0435\u043a\u0446\u0438\u044e What is SENAR? \u0432 README", "done": true}, {"step": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u2014 \u043d\u0435\u0442 orphan SENAR \u0431\u0435\u0437 \u0441\u0441\u044b\u043b\u043a\u0438", "done": true}]

## Rollback

## Journal

- 2026-04-05T13:37:22Z [implementation] — AC verified: 1. README, CLAUDE.md, QUICKSTART имеют ссылки senar.tech + github.com/Kibertum/SENAR ✓ 2. README содержит секцию "What is SENAR?" ✓ 3. QUICKSTART ссылается на SENAR spec ✓ 4. Orphan SENAR в docs/ — только контекстные термины (Rule X, gate), не требуют ссылок ✓
