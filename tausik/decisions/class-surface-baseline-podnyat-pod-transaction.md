---
slug: class-surface-baseline-podnyat-pod-transaction
task: null
date: "2026-09-06"
edges: []
---

## Decision

class_surface baseline поднят под transaction(): SQLiteBackend 158→159 (+1, единственный новый публичный член — контекстный менеджер BackendTransactionMixin.transaction). Рост оплачен УДАЛЕНИЕМ трёх РУЧНЫХ копий приёма владения (owns_tx в service_adapts.adapt_delta, service_actz.actz_delta, service_task._write_update_atomically) и переводом ВОСЬМИ из девяти площадок begin_tx на один вызов: поверхность класса выросла на единицу, а число мест, где правило владения приходится ПОМНИТЬ, упало с девяти до нуля. ProjectService не изменился (143): transaction() живёт на бэкенде, служба его только вызывает. Альтернатива — сделать begin_tx/commit_tx/rollback_tx приватными и уронить поверхность до 156 — отвергнута В ЭТОЙ задаче: их публично зовут пины транзакционного поведения (tests/test_adapts.py, tests/test_projection_follows_the_write.py), играющие роль вызывающего-владельца, и переписывание этих тестов выходит за границу «чинить, не открыв дыру». Кандидат на отдельную задачу.

## Rationale
