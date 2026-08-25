---
slug: hash-chain-events-na-insert-time-event-add-vychislyaet-prev
title: "Hash-chain events на insert-time (event_add вычисляет prev_hash/entry_hash при вставке)"
type: dead_end
tags:
  - audit
  - renar
  - sqlite
  - triggers
task: v16r-audit-hashchain
edges: []
---

Approach: Hash-chain events на insert-time (event_add вычисляет prev_hash/entry_hash при вставке)
Reason: Большинство событий пишутся SQL audit-триггерами (tasks_audit_insert/status/claim/delete), минуя Python event_add. SQLite-триггер не может вызвать sha256/JCS-канонизацию → chained-на-insert даёт смесь chained+NULL строк, ломая verify. Решение: lazy monotonic sealing (seal по id>frontier on-demand, atomic). См. decision #101.
