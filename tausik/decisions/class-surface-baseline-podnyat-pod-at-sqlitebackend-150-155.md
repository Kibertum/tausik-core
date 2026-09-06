---
slug: class-surface-baseline-podnyat-pod-at-sqlitebackend-150-155
task: at-acceptance-tests-derived-by-an-isolated-agent
date: "2026-09-06"
edges: []
---

## Decision

class_surface baseline поднят под AT: SQLiteBackend 150→155 (+5: AtCrudMixin), ProjectService 134→140 (+6: AtMixin). Осознанный ratchet-forward, та же природа, что решения #327/#328.

## Rationale

at-acceptance-tests-derived-by-an-isolated-agent добавила AtMixin/AtCrudMixin по тому же паттерну ActzMixin/AdaptsMixin — новая RENAR-сущность, не god-object дрейф.
