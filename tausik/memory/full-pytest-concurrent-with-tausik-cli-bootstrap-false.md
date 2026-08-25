---
slug: full-pytest-concurrent-with-tausik-cli-bootstrap-false
title: "Full pytest concurrent with tausik CLI/bootstrap → false config-mutation teardown error"
type: gotcha
tags:
  - config
  - dogfooding
  - flaky
  - pytest
  - testing
task: null
edges: []
---

Running the FULL pytest suite in the background while simultaneously issuing tausik operations (task update/verify/task done, bootstrap --ide all) triggers a false-positive teardown ERROR in tests that guard the live .tausik/config.json against mutation (e.g. test_scope_write_gate_hook.py::TestHook::test_no_declared_scope_anywhere_grants_legacy_freedom). The teardown hashes .tausik/config.json at setup vs teardown; my concurrent CLI/bootstrap writes to .tausik/ change it mid-test, and the guard reports 'Test mutated the live project config' even though the test passed and no test code leaked. The test passes cleanly in isolation. **How to avoid:** do not run task_done/verify/bootstrap while a full-suite background run is live; run the full suite to completion first, or fence tausik CjcLI ops until it finishes. This is a dogfooding artifact of using the framework on itself while its own suite runs, not a code defect.
