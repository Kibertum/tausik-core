---
slug: for-environment-conditional-pytest-skips-use-pytestmark
task: hotfix-skill-bundles-skip-must-not-change-test-cou
date: "2026-05-07"
edges: []
---

## Decision

For environment-conditional pytest skips, use `pytestmark = pytest.mark.skipif(...)` instead of `pytest.skip(..., allow_module_level=True)`.

## Rationale

module-level pytest.skip removes tests from `pytest --collect-only` output entirely. scripts/gen_doc_constants.py uses count_tests (which parses --collect-only summary) as the canonical source for `test_count` in docs/_generated/constants.json. Module-level skip → test_count drifts between local and CI → doc-constants drift check breaks CI. pytestmark.skipif is run-time skip, collection still counts the tests, so the count is environment-stable.
