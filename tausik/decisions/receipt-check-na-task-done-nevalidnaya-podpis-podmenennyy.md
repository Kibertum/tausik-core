---
slug: receipt-check-na-task-done-nevalidnaya-podpis-podmenennyy
task: v15-receipt-check-on-done
date: "2026-06-12"
edges: []
---

## Decision

Receipt-check на task_done: невалидная подпись/подменённый receipt (slug или ran_at не совпадают со строкой run) = БЛОК; git_sha drift = warning (коммит в середине задачи легитимен); NULL receipt / нет ключа = graceful pass с warning

## Rationale

Блокировать только то, что доказывает tampering. Drift HEAD между verify и done — нормальный воркфлоу (коммит после подзадачи). Pre-v29 строки и keyless-проекты не должны ломаться (обратная совместимость).
