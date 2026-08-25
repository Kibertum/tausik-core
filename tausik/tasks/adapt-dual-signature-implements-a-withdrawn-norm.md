---
slug: adapt-dual-signature-implements-a-withdrawn-norm
title: "ADAPT требует двойной подписи — норму, которую ADR-011 отозвал как фикцию"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 60
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

Команда `tausik adapt sign` объявляет в справке «Record a dual signature (§7.5); architect → ed25519». RENAR ADR-011 (accepted) подпись клиента с ADAPT СНЯЛ, и назвал причину: клиент подписывал инженерный документ, которого не читал и не мог оценить. Граница проведена по АУДИТОРИИ, а не по содержанию: показанное клиенту и утверждённое есть обязательство и живёт в ACTZ; не показанное есть интерпретация и живёт в ADAPT. Следствия для нас: подписывает ТОЛЬКО архитектор; состояние `client-ready` изымается из машины состояний ADAPT, потому что вынесение вопросов клиенту стало предметом ACTZ; каждая обратная находка обязана нести `decided-in` на пункт ПОДПИСАННОГО ACTZ. Задача: привести реализацию к принятой редакции, а не дописать ACTZ рядом со старым поведением. Отдельно проверить, что уже подписанные ADAPT в живых базах не становятся невалидными молча — миграция обязана назвать, что произошло. Это долг, а не улучшение: мы объявляем себя эталонной реализацией и предъявляем отозванную норму.

## Acceptance Criteria

## Plan

## Rollback

## Journal
