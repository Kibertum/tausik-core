---
slug: rasshiryaya-signaturu-inventar-snimay-po-potrebitelyam
title: "Расширяя сигнатуру, инвентарь снимай по ПОТРЕБИТЕЛЯМ функции, а не только по месту дефекта"
type: convention
tags:
  - inventory
  - senar
  - signature
task: memory-route-gate-did-not-get-the-base-directory
edges:
  - relation: relates_to
    target_type: memory
    target: inventar-snimay-po-vyzovu-i-roli-dovoda-a-ne-po-imeni
---

Замер #206. В #205 базовый каталог протянут в write_targets, инвентарь снимался по вызовам join(project_dir и по вызовам самой функции - и оба раза был ПОЛОН. Пропущен близнец write_targets_with_confidence: он не место дефекта и не вызывает join, он ПОТРЕБИТЕЛЬ расширяемой сигнатуры. Один гейт починен, второй с тем же разбором - нет. Правило: когда правка МЕНЯЕТ СИГНАТУРУ, у инвентаря появляется третья ось - кто эту функцию вызывает и кто её дублирует. Дополняет #522 (по вызову и роли довода), не заменяет.
