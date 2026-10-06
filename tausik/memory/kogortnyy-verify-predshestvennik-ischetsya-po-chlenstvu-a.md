---
slug: kogortnyy-verify-predshestvennik-ischetsya-po-chlenstvu-a
title: "Когортный verify: предшественник ищется по членству, а не по identity; исполнение — делегированием"
type: pattern
tags:
  - "verify,cohort,pooled,invariant"
task: r1112-cohort-receipts-and-incremental-rerun
edges: []
---

r1112-cohort-receipts (доказательство: tests/test_verify_cohort.py, verify #3577): (1) инвалидация когорты обязана искать предшественника по members_json, не по identity — правка участника меняет identity, и матчинг по identity промахивается ровно по тому дрейфу, который надо именовать; (2) пул-верификация наследует кэш-гарды однозадачной линии делегированием в run_verify_for_task с явным union-скопом, а не собственным вызовом gate_runner — класс дефекта cli-verify-bypasses-cache-guards структурно невозможен; (3) 'пропал' и 'изменён' — разные инвалидаторы: проверка missing-evidence идёт раньше общего диффа фингерпринтов, у них разные средства исправления.
