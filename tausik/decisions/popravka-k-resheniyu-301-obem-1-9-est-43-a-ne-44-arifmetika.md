---
slug: popravka-k-resheniyu-301-obem-1-9-est-43-a-ne-44-arifmetika
task: null
date: "2026-09-01"
edges: []
---

## Decision

ПОПРАВКА К РЕШЕНИЮ #301: ОБЪЁМ 1.9 ЕСТЬ 43, А НЕ 44. Арифметика: было 42, закрыта одна (ci-does-not-run-on-the-release-branch из standards-drift-detection), заведено две — 42 минус 1 плюс 2 равно 43. В #301 сумма записана неверно при верном перечне по историям. СЧЁТ, ПЕРЕСЧИТАННЫЙ КОМАНДОЙ ПОСЛЕ ЗАВЕДЕНИЯ: gates-declare-what-they-prevent 15, evidence-primitives 8, renar-debt-implemented-wrong 8, renar-contract-contour 5, test-evidence-not-test-volume 4, standards-drift-detection 3 — сумма 43. Точки остатка: 35, 38, 37, 39, 42, 40, 42, 43. Пополнение (плюс 2) снова превысило закрытие (1), равновесие смены #204 трендом не стало. Правило, оплаченное этой ошибкой: сумму объёма БЕРИ ИЗ ПЕРЕСЧЁТА КОМАНДОЙ, а не складывай в уме при записи решения.

## Rationale

Ошибка найдена собственным пересчётом по шести историям сразу после записи решения #301; исправлена до передачи смены, а не после.
