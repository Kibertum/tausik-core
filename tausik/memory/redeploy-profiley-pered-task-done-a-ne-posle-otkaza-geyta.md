---
slug: redeploy-profiley-pered-task-done-a-ne-posle-otkaza-geyta
title: "Редеплой профилей — ПЕРЕД task done, а не после отказа гейта"
type: convention
tags: []
task: null
edges: []
---

bootstrap_drift сравнивает развёрнутые копии в профилях хостов с источником, и правка в scripts/ или harness/ до редеплоя означает, что запускается старый код. За смену #277 этот отказ случился трижды, каждый раз на закрытии, и каждый раз стоил лишнего verify — а лишний оборот в этом проекте измерен как ~482k токенов cache_read. Порядок: правка → python bootstrap/bootstrap.py --ide all → CHANGELOG → verify → task done. Побочное следствие отказа: красный прогон требует dead-end или NO-DEAD-END, то есть ещё один вызов.
