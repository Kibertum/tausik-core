---
slug: obyavit-binarnyy-pdf-v-relevant-files-chtoby-zakryt-zadachu
title: "Объявить бинарный PDF в relevant_files, чтобы закрыть задачу через verify вместо флага --no-file-cha"
type: dead_end
tags: []
task: null
edges: []
---

Approach: Объявить бинарный PDF в relevant_files, чтобы закрыть задачу через verify вместо флага --no-file-changes
Reason: Гейт filesize не фильтрует по типу файла и посчитал строки в сжатом потоке PDF: 9897 и 45795 при лимите 500. Закрытие заблокировано отказом по несуществующему нарушению. Путь непроходим, пока не закрыта filesize-gate-counts-lines-in-binary-files. Второй отвергнутый вариант — ограничить проверку чистого дерева pathspec'ом по одним лишь PDF — отвергнут НЕ по технической причине: он проходит гейт, но делает это ложным утверждением о содержимом дерева.
