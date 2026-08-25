---
slug: accumulation-workflow-git-user-gated-over-declaration
title: "Accumulation-workflow: git-user-gated → over-declaration инфлейтит complexity-детектор"
type: gotcha
tags: []
task: null
edges: []
---

Когда коммит отложен (git за апрувом), незакоммиченные правки прошлых задач копятся. verify git-cross-check (is_declared_consistent_with_git_diff) требует declared ⊇ actual-since-start, вынуждая объявлять ВЕСЬ незакоммиченный набор в relevant_files. Но warn_if_understated считает те же relevant_files → 'COMPLEXITY UNDERSTATED: 22 files → complex' на honest-medium задаче. Оба гейта ключуются на relevant_files, и over-declaration ради cross-check ложно триггерит complexity. Чистое решение: per-task commit чистит дерево. Смежно [[277]]. Кандидат на фикс: complexity-детектор должен считать файлы, реально изменённые ПОСЛЕ started_at этой задачи (git diff since started_at), а не полный declared-набор.
