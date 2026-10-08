---
slug: run-a-guessed-set-of-migration-and-cli-test-filenames-in
title: "Run a guessed set of migration and CLI test filenames in one scoped pytest command"
type: dead_end
tags:
  - pytest
  - test-selection
task: route-ship-by-residual-assurance
edges: []
---

Approach: Run a guessed set of migration and CLI test basenames in one scoped pytest command. Reason: The repository uses test_migrations.py and does not contain the guessed backend-migrations, migrations-parity, or project-cli-review basenames; pytest aborted collection. Enumerate actual filenames with rg before retrying.
