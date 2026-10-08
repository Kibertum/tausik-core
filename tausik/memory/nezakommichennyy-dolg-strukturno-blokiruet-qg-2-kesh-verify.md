---
slug: nezakommichennyy-dolg-strukturno-blokiruet-qg-2-kesh-verify
title: "Незакоммиченный долг структурно блокирует QG-2: кэш verify отказывает узкой области в грязном дереве"
type: gotcha
tags:
  - git
  - qg2
  - senar
  - verify
task: test-ddl-drift-verification-runs
edges: []
---

В сессии #121 работа по задаче была закончена и зелёная (полный набор в обоих режимах), а `task done` не проходил. Причина оказалась НЕ в задаче.

МЕХАНИЗМ. В дереве лежали 135 изменённых файлов — работа сессий #117-#120, ни разу не закоммиченная. Объявленные relevant_files задачи были СТРОГИМ ПОДМНОЖЕСТВОМ того, что видит `git diff HEAD` + `git log --since`, а на строгом подмножестве кэш verify отказывается сертифицировать: cache_status='git-mismatch' (verify_cached_run.py, защита от подмены узкой областью). `tausik verify` при этом отвечает passed=True — прогон зелёный, но переиспользован быть не может, и `task done` честно говорит «no fresh verify run».

ГЕЙТ ПРАВ, ЭТО НЕ ДЕФЕКТ. Сертифицировать узкую область посреди широкого грязного дерева нельзя — иначе receipt подписывал бы 13 файлов, пока менялось 135.

ЧТО ЭТО ЗНАЧИТ ПРАКТИЧЕСКИ. Незакоммиченная работа перестаёт быть пассивным долгом и НАЧИНАЕТ ОСТАНАВЛИВАТЬ РАБОТУ: блокируется закрытие ЛЮБОЙ новой задачи, а не только той, чьи файлы лежат в дереве. Диагностируется мгновенно по паре признаков: verify passed=True + cache_status='git-mismatch' + task done «no fresh verify run». Лечится коммитом, а не правкой задачи.

ВТОРОЙ ПОРЯДОК ОПЕРАЦИЙ, который тоже стоил попытки: relevant_files надо объявить ДО verify. Если verify отработал на задаче с пустыми relevant_files, он сертифицирует пустую область (scoped-гейты SKIP) — и task done это отвергнет отдельным сообщением «declares no relevant_files». Правильная последовательность: task update --relevant-files -> verify --task -> task done.

Связано: [[kesh-verify-sertifikat-privyazan-k-obyavlennoy-oblasti]].
