---
slug: re-export-from-sibling-module-breaks-monkeypatch-setattr
title: "Re-export from sibling module breaks monkeypatch.setattr(host, ...) in tests"
type: gotcha
tags:
  - module-split
  - monkeypatch
  - refactor
  - testing
task: fix-verify-cache-relevant-files-bypass
edges: []
---

When a function `foo` is moved from `host_module.py` to `helper_module.py` and re-exported via `from helper_module import foo`, existing tests that do `monkeypatch.setattr(host_module, "foo", fake)` ONLY rebind the host module's name. Code that internally calls `foo` from `helper_module` namespace still sees the real function. v1.3.4 hit this: I extracted `changed_files_since` from service_verification.py to verify_git_diff.py; tests patching `sv.changed_files_since` started failing because run_gates_with_cache calls is_declared_consistent_with_git_diff (still in verify_git_diff), which calls changed_files_since by direct lookup in its own module. Fix: patch `verify_git_diff.changed_files_since` instead. Rule of thumb: if you patch a function used INTERNALLY by another function in the same module, patch where it LIVES, not where it's re-exported.
