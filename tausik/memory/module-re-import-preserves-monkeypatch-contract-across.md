---
slug: module-re-import-preserves-monkeypatch-contract-across
title: "Module re-import preserves monkeypatch contract across filesize splits"
type: pattern
tags:
  - filesize-gate
  - module-split
  - monkeypatch
  - python-imports
  - testing
task: v14b-followup-brain-init-filesize-debt
edges: []
---

When splitting a large module M into M + M_extracted, and the test suite contains `monkeypatch.setattr(M.dependency_module, "func", ...)`, the patched attribute lookup goes through M's module-level `import dependency_module` reference. After the split, if M no longer uses `dependency_module` directly (only M_extracted does), removing `import dependency_module` from M breaks the test.

Fix: keep `import dependency_module  # noqa: F401  re-export so tests can monkeypatch via M.dependency_module` at module level in M. Modules are sys.modules singletons — `monkeypatch.setattr(M.dependency_module, "func", ...)` mutates the SAME module object that M_extracted's own `import dependency_module` resolves to, so the patch propagates transparently.

Concrete case (v14b-followup-brain-init-filesize-debt): tests/test_brain_init.py:559 does `monkeypatch.setattr(brain_init.brain_project_registry, "register_project", boom)`. After moving register_project's call sites into brain_init_create.py, removing `import brain_project_registry` from brain_init.py made the test fail with AttributeError. Re-adding the import as a `# noqa: F401` re-export fixed it without changing test code.

When to apply: any filesize-debt split where module-level imports of dependency modules might be reachable via test monkeypatches. Run the test suite BEFORE removing module-level imports that look "unused" — Python's import-as-side-effect makes them part of the module's public surface.
