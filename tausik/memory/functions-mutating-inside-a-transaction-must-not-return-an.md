---
slug: functions-mutating-inside-a-transaction-must-not-return-an
title: "Functions mutating inside a transaction must not return an in-loop counter on the rollback path"
type: gotcha
tags:
  - correctness
  - migration
  - rollback
  - transaction
task: v34-backfill-return-0-not-partial-count-after-mid-
edges: []
---

maybe_backfill_v34 (backend_migrations_v34.py) accumulated a 'sealed' counter in the loop and had one `return sealed` after try/except — so the except branch (which rolls back) fell through and returned the partial count, claiming rows were sealed when rollback committed nothing. Rule: any function that writes inside a BEGIN/commit and may roll back must have the rollback branch return the committed count (usually 0), not the in-progress counter. Caught by adversarial review in #89; fixed with an explicit `return 0` in the except.
