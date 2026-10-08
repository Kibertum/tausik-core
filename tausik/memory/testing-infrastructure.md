---
slug: testing-infrastructure
title: "Testing infrastructure"
type: context
tags:
  - infrastructure
  - testing
task: null
edges: []
---

134 tests in 3 files: test_frai_backend.py (62 tests, raw SQLite ops), test_frai_service.py (54 tests, business logic), test_frai_cli.py (18 tests, CLI integration). Run: .frai/venv/Scripts/python -m pytest tests/ -v. Fixtures in conftest.py use tmp_path for DB isolation. Zero external deps — only pytest.
