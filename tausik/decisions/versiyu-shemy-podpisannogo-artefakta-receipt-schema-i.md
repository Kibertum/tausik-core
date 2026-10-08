---
slug: versiyu-shemy-podpisannogo-artefakta-receipt-schema-i
task: risk-gate-coverage-configured-count-in-check
date: "2026-07-27"
edges: []
---

## Decision

Версию схемы подписанного артефакта (RECEIPT_SCHEMA и подобные) бампать ТОЛЬКО когда новое поле меняет то, что артефакт УТВЕРЖДАЕТ. Аддитивное поле-телеметрия с fallback на стороне читателя (отсутствие → прежнее поведение) версию НЕ бампает.

## Rationale

configured_gates_count добавлен в receipt без бампа v2→v3, в отличие от declared_scope (v1→v2). Различие: declared_scope изменил СМЫСЛ (рецепт v1 теперь трактуется как scope=UNVERIFIED — читатель ОБЯЗАН различать версии). configured_gates_count ничего нового не утверждает о полноте покрытия — это вход для риск-модели, и рецепт без него не «неверен», читатель просто пересчитывает как раньше. Верификация version-agnostic (ре-канонизирует хранимые байты, не ветвится на строку схемы/набор полей), поэтому старые и новые рецепты одной версии проверяются идентично. Бамп версии без семантической необходимости = лишний blast radius (export-тесты, compliance-матрица, все читатели строки схемы). Подтверждено L3-ревьюером (opus). task=risk-gate-coverage-configured-count-in-check.
