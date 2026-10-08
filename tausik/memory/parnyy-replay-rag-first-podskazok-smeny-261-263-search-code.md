---
slug: parnyy-replay-rag-first-podskazok-smeny-261-263-search-code
title: "Парный replay rag-first подсказок, смены #261–#263: search_code = 0 в обоих условиях, экономии нет, точка 1.9 закрыта"
type: context
tags:
  - benchmark
  - rag
  - release-1.9
  - replay
  - tokens
task: v14b-rag-nudge-replay-benchmark
edges: []
---

Протокол docs/ru/research/rag-nudge-replay-protocol.md прогнан целиком (§7): B без подсказок (сессия 3a21939b) и A с подсказками (ed5c389a), один коммит 396de834, claude-opus-5[1m], десять фиксированных вопросов, сверка §4 сошлась в обоих. Основная метрика Σ cache_creation + Σ output: B 195 055, A 198 848 (+1,9 %); байты результатов исследования B 292 715, A 326 323 (+11,5 %); cache_read A −9,8 %; вызовов инструментов B 76, A 62. Твёрдый факт — search_code вызван 0 раз в A и 0 раз в B: подсказки не меняют выбор инструмента, только форму (меньше Grep, больше и крупнее Read). Повтор условия B (B1 с одним просочившимся nudge) отличался от чистого B на +13 %/+25 % — дельта A−B внутри шума. Утверждение «подсказки экономят» по §4 не допускается; обещание экономии в README/заметках остаётся снятым (условие 1 выпуска). Три следствия заведены задачами в 1.10: status-takes-five-seconds-on-a-missing-defect-of-index, session-metrics-sums-usage-once-per-content-block, rag-first-nudges-do-not-change-tool-choice. Улики локально в docs/ru/research/_internal/rag-replay/2026-09-14/ (gitignored). Закрытием задачи v14b-rag-nudge-replay-benchmark автозакрыты история release19-effective-context и эпик release-19-agent-effectiveness — состав 1.9 по решению #370 закрыт полностью.
