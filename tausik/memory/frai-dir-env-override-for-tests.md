---
slug: frai-dir-env-override-for-tests
title: "FRAI_DIR env override for tests"
type: gotcha
tags:
  - isolation
  - testing
task: null
edges: []
---

Tests use FRAI_DIR env variable to isolate DB in tmp directories. Defined in project_config.find_frai_dir(). Without this, tests would use the real .frai/frai.db. conftest.py fixtures (tmp_db, backend, svc) handle isolation automatically.
