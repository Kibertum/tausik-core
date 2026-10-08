---
slug: menyaya-opublikovannyy-artefakt-snimay-inventar-vseh-ego
title: "Меняя опубликованный артефакт, снимай инвентарь ВСЕХ его издателей: у манифеста RENAR их два — YAML и renar/conformance.md"
type: convention
tags:
  - artifact
  - export
  - inventory
  - renar
task: mandatory-clauses-are-constants-published-as-earned
edges: []
---

#213, найдено ревью: блок mandatory-clauses-basis добавлен в RENAR-CONFORMANCE.yaml (build_manifest), а renar_export._conformance_doc продолжал публиковать семь голых булевых — второй git-tracked артефакт, который генерируется `tausik renar export` и проверяется `--check`. Он импортирует eval_mandatory_clauses напрямую и брал из вердиктов только c["confirmed"], выбрасывая basis. Правило: правя состав публикуемого блока, ищи потребителей ПО ВЫЗОВУ функции-источника (grep eval_mandatory_clauses / build_manifest), а не только по имени поля; в scope задачи включай renar_export.py. Порядок регенерации: bootstrap --ide all → --check → renar conformance --write → renar export → export --check.
