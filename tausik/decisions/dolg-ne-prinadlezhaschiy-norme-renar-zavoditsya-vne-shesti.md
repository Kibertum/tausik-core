---
slug: dolg-ne-prinadlezhaschiy-norme-renar-zavoditsya-vne-shesti
task: null
date: "2026-09-04"
edges: []
---

## Decision

ДОЛГ, НЕ ПРИНАДЛЕЖАЩИЙ НОРМЕ RENAR, ЗАВОДИТСЯ ВНЕ ШЕСТИ ИСТОРИЙ И ОБЪЁМ 1.9 НЕ РАЗДУВАЕТ. В #210 заведено шесть таких: renar-conformance-py-has-one-line-of-headroom, verify-handle-check-py-has-four-lines-of-headroom, powershell-channel-cannot-read-python-dash-c, tools-spec-adds-a-possibly-nonexistent-dir-to-syspath, xargs-executes-its-arguments, task-gate-blocks-writes-outside-the-project-tree. Это техдолг размера файлов, гигиена импорта, поведение инструментального канала и границы хука — предметы реальные, но к соответствию стандарту отношения не имеющие. Владелец может перенести любую в историю; по умолчанию они НЕ блокируют релиз и НЕ считаются в 32.

## Rationale

Иначе одно из двух: либо долг теряется, либо объём релиза перестаёт означать «что осталось до соответствия».
