---
slug: actz-the-contract-contour-artifact-is-missing
title: "ACTZ — протокол уточнения ТЗ: контрактного артефакта нет вовсе"
status: planning
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: null
role: architect
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

RENAR §5A (ADR-011, accepted) вводит ACTZ — артефакт контрактного контура: протокол уточнения ТЗ с двусторонней подписью, контрактным весом и жизненным циклом draft → sent → signed → superseded. Кардинальность 0..N на ТЗ и 1..N на ADAPT. Поздний протокол, оформленный после демонстрации, есть ШТАТНЫЙ случай, а не исключение. Договорное имя — «Протокол уточнения ТЗ № N»; слово «акт» в корпусе запрещено и зарезервировано за документами сдачи-приёмки, значит наш вывод не имеет права его печатать. У нас этого артефакта нет ни в схеме, ни в CLI, ни в MCP. Задача: завести сущность с жизненным циклом и подписями по образцу существующего adapt (ed25519 уже есть, изобретать подпись не надо), плюс ребро decided-in от обратной находки ADAPT на пункт подписанного ACTZ. НЕГАТИВНОЕ ограничение: ADR-017 «односторонняя приёмка» имеет статус proposed и задевает именно двустороннюю подпись. Реализовать двусторонность так, чтобы односторонний случай позже добавлялся, а не ломал сделанное — но САМ односторонний случай сейчас НЕ реализовывать (решение #255).

## Acceptance Criteria

## Plan

## Rollback

## Journal
