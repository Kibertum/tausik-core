---
slug: svoy-spisok-obema-dogadka-poka-ne-sveren-inventarem
title: "Свой список объёма — догадка, пока не сверен ИНВЕНТАРЁМ"
type: convention
tags: []
task: write-gate-resolves-relative-paths-against-the-wrong-directory
edges: []
---

В #205 я объявил scope-paths до инвентаря и ошибся дважды: назвал несуществующий pwsh_write_gate.py и пропустил memory_pretool_block.py, где было то же самое отождествление. Поймал scope-ACL, а не я. Порядок: сперва инвентарь ПЕРЕЧНЕМ по признаку кода (здесь — grep по join(project_dir,...)), потом объявление объёма.
