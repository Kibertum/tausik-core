---
slug: adding-tests-to-test-gen-doc-constants-invalidates
title: "Adding tests to test_gen_doc_constants invalidates constants.json test_count"
type: gotcha
tags:
  - constants-json
  - gen-doc-constants
  - self-modifying-suite
  - test-count
task: v14b-doc-gen-test-count
edges: []
---

When you add new tests anywhere in the suite (including tests/test_gen_doc_constants.py itself), the live `pytest --collect-only` count grows by N and `test_constants_json_file_matches_live` starts failing with `'test_count': X != Y`. Workflow: after writing tests, regenerate `docs/_generated/constants.json` (`python scripts/gen_doc_constants.py` — spawns pytest collection, ~1.4s), THEN run pytest. Forgetting this looks like a "regression in unrelated test" but it's just stale on-disk constants. Same applies to MCP tool counts when adding/removing TOOLS entries.
