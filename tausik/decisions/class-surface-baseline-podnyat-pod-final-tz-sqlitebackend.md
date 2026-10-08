---
slug: class-surface-baseline-podnyat-pod-final-tz-sqlitebackend
task: final-tz-is-the-acceptance-reference-and-we-have-none
date: "2026-09-06"
edges: []
---

## Decision

class_surface baseline поднят под final-tz: SQLiteBackend 148→150 (+2: actz_points_with_completion, orphan_signed_points), ProjectService 132→134 (+2: final_tz_snapshot, orphan_signed_points). Осознанный ratchet-forward, та же природа, что и решение #327.

## Rationale

final-tz-is-the-acceptance-reference-and-we-have-none добавила 2 read-only производных метода на каждом уровне (CRUD/сервис) для §5A.4 (итоговое ТЗ, orphan-детектор) — новая read-only функциональность над уже существующими таблицами ACTZ, не god-object дрейф.
