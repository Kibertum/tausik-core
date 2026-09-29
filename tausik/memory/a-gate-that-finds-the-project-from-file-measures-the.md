---
slug: a-gate-that-finds-the-project-from-file-measures-the
title: "A gate that finds 'the project' from __file__ measures the framework, not the project"
type: pattern
tags:
  - "gates,project-root,windows"
task: null
edges: []
---

Walking up from the gate's own file to .git lands on the project only when the gate runs from the deployed copy inside it. From the framework tree (submodule CLI, sandbox, global install) it lands on the FRAMEWORK: test_dedupe measured framework tests in a consumer close, ruff_format raised 'path is on mount C:, start on mount D:', cross_model_parity crashed looking for bootstrap/ under .claude/. Rule: resolve the project from its .tausik/ (scripts/gate_project_root.py::project_root), fall back to the old walk only when none exists. Found by running tausik demo, session #279.
