---
slug: class-surface-baseline-tausik-gates-json-podnyat-pod-actz
task: actz-the-contract-contour-artifact-is-missing
date: "2026-09-06"
edges: []
---

## Decision

class_surface baseline (tausik/gates.json) поднят под ACTZ: SQLiteBackend 129→148 (+19, ActzCrudMixin), ProjectService 118→132 (+14, ActzMixin). Осознанный ratchet-forward, не тихий: новая сущность ACTZ (13 сервисных методов + CRUD) закономерно расширяет композитную поверхность обоих классов, ровно как AdaptsMixin/AdaptsCrudMixin уже сделали это для тех же двух классов ранее. Измерено tests/test_gate_class_surface.py::measure() после добавления ActzMixin/ActzCrudMixin.

## Rationale

Гейт class_surface (tausik/gates.json) требует точного совпадения actual==baseline и растёт только по явному решению ("ratchet, may only shrink [for unbaselined growth]; changing the baseline itself is a reviewable move"). Задача actz-the-contract-contour-artifact-is-missing добавила ActzMixin/ActzCrudMixin по тому же паттерну, каким AdaptsMixin/AdaptsCrudMixin уже используются — расширение публичной поверхности здесь не god-object дрейф, а прямое следствие новой RENAR-сущности того же класса, что ADAPT.
