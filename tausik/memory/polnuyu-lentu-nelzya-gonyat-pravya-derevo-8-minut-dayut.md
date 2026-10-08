---
slug: polnuyu-lentu-nelzya-gonyat-pravya-derevo-8-minut-dayut
title: "Полную ленту нельзя гонять, правя дерево: 8 минут дают ложные «дефекты»"
type: gotcha
tags: []
task: "683-structurally-identical-tests-in-294-groups"
edges: []
---

Смена #277: полный прогон при одновременной правке файлов и bootstrap --ide all дал 15 отказов, из которых 12 — мои же правки на лету. Красным становится ровно то, что читает СОСТОЯНИЕ ДЕРЕВА: bootstrap_drift, ruff_format.legacy, mypy_clean, comment_history_refs, repo_coherence, gates_record_non_execution. На тихом дереве 15 → 3. Правило: полная лента — последнее действие перед закрытием, и до её конца не трогать ни файлы, ни bootstrap. Цена нарушения — восемь минут плюс разбор пятнадцати мнимых дефектов.
