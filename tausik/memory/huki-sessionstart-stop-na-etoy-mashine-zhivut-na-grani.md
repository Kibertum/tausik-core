---
slug: huki-sessionstart-stop-na-etoy-mashine-zhivut-na-grani
title: "Хуки SessionStart/Stop на этой машине живут на грани таймаута: status идёт 5,3 с, и контекст молча не доходит"
type: gotcha
tags:
  - hooks
  - index
  - performance
  - session-start
  - sqlite
task: status-takes-five-seconds-on-a-missing-defect-of-index
edges: []
---

session_start.py и session_cleanup_check.py занимают ~5,9 с при таймаутах 6 с и 5 с — в пробном безголовом прогоне SessionStart был отменён (hook_cancelled, timedOut) и весь автовставляемый контекст TAUSIK (активные задачи, память, подсказки) не попал в сессию; никакой ошибки при этом не видно. Причина не в хуках: `tausik status` тратит 5,04 с из 5,3 с в одной корреляционной EXISTS(SELECT 1 FROM tasks d WHERE d.defect_of = t.slug) по 1504 done-строкам — на tasks.defect_of нет индекса, а соседний EXISTS по verification_runs с idx_verify_task идёт 0,0 с. Пока не починено (status-takes-five-seconds-on-a-missing-defect-of-index), любой замер, где важна доставка контекста, должен проверять по транскрипту, что SessionStart не отменён; поднимать таймауты в развёрнутом settings.json можно только на время замера с побайтовым восстановлением (bootstrap --ide claude восстанавливает; cmp с бэкапом).
