---
slug: optional-deps-must-be-lazy-imported-in-cli-reachable
title: "Optional deps must be lazy-imported in CLI-reachable modules; fresh-clone smoke is the only catch"
type: gotcha
tags:
  - "0-deps"
  - cli
  - dependencies
  - release
  - smoke
task: v151-fix-yaml-hard-import
edges: []
---

A module-level `import <optional-dep>` (e.g. PyYAML) in ANY module reachable from project.py breaks EVERY `tausik` CLI command on a clean install — the .tausik/venv carries only declared deps, and TAUSIK's core CLI contract is stdlib-only. v1.5.0 shipped this bug: project.py imports cmd_renar unconditionally → project_cli_renar → renar_conformance/renar_export each did `import yaml` at module top → ModuleNotFoundError on every command (init/status/task) for new users. Fix: lazy-import optional deps INSIDE the functions that use them (renar render/export), degrading with a clear 'pip install X' message. Guards: (1) AST test asserting no module-level optional-dep import in CLI-core modules (tests/test_no_hard_yaml_import.py); (2) AST scan of all scripts/ for non-stdlib top-level imports; (3) MANDATORY fresh-clone smoke in the release checklist — clone the published tag, `bootstrap --init` on a python WITHOUT the optional deps, reach a working `tausik status`. The dogfood machine HAS pyyaml so unit/integration tests never caught it — only the clean-clone smoke did. Add fresh-clone smoke to v15p-release-150-style release gates.
