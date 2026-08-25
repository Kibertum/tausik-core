---
slug: test-count-v-doc-constants-nizhnyaya-granitsa-n-testov-a-ne
task: doc-constants-drift-is-a-trap-every-task-steps-in
date: "2026-07-26"
edges: []
---

## Decision

test_count в doc-constants — НИЖНЯЯ ГРАНИЦА ('N+ тестов'), а не exact-pin: рост набора не дрейф, падает только усадка ниже записанного числа

## Rationale

Трап: test_count — производное ИЗМЕРЕНИЕ, меняется почти от каждой задачи, но проверялся как DECLARED-константа (exact-pin) → полный набор краснел после каждого добавления тестов (test_check_docs_hook::test_exit_0). Из 4 опций задачи выбрана уточнённая (г): lower-bound семантика. Рост (stored ≤ live) не дрейф → трап закрыт полностью, ноль остатка. Усадка (stored > live) и doc-overclaim (found > live) остаются красными — единственные ОСМЫСЛЕННЫЕ провалы (набор реально сократился / доки обещают больше тестов чем есть). Сохраняет проверяемый факт в значимом направлении, в отличие от чистой (г). version/tool/code counts остаются exact-pin — это DECLARED intent, не измерение. --skip-test-count для CI-variance (importorskip collects fewer) сохранён.
