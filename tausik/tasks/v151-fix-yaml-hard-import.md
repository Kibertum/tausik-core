---
slug: v151-fix-yaml-hard-import
title: "[P0] CLI broken on clean install — lazy-import yaml in renar modules (fresh-clone smoke caught it)"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: v15p-release-150
scope: "scripts/project_cli_renar.py, scripts/renar_conformance.py, scripts/renar_export.py, tests/test_no_hard_yaml_import.py"
scope_exclude: "no new dependency added; RENAR feature behavior unchanged when yaml present"
relevant_files:
  - "scripts/project_cli_renar.py"
  - "scripts/renar_conformance.py"
  - "scripts/renar_export.py"
  - "tests/test_no_hard_yaml_import.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T23:22:16Z"
---

## Goal

The fresh-clone smoke of the published v1.5.0 found that EVERY `tausik` CLI command crashes on a clean install with ModuleNotFoundError: No module named 'yaml' — project.py imports cmd_renar unconditionally, and project_cli_renar.py (+ renar_conformance.py, renar_export.py) do a module-level `import yaml`, but PyYAML is NOT a core dependency (the '0 dependencies, stdlib-only CLI' contract). Fix: make yaml a LAZY import inside the renar functions that need it, so the core CLI (init/status/task/etc.) loads without yaml; renar conformance/export degrade with a clear 'pip install pyyaml' message when yaml is absent, instead of breaking the whole CLI.

## Acceptance Criteria

AC1: project_cli_renar.py, renar_conformance.py, renar_export.py have NO module-level `import yaml` — it's imported lazily inside the functions that use it. AC2: importing project.py / running a core CLI command (init, status, task) succeeds with PyYAML absent (no ModuleNotFoundError). AC3: renar conformance/export with yaml absent fail with a clear actionable message ('pip install pyyaml'), not a traceback, and do not break other commands. AC4: a regression test asserts (via AST) that the CLI-core renar modules carry no top-level third-party yaml import. AC5: fresh-clone smoke of the fixed tree (bootstrap --init in a clean checkout, yaml not guaranteed) reaches a working `tausik status`. AC6: ruff+mypy clean; filesize<400. Negative: yaml-absent → renar command prints the install hint + non-zero exit, the rest of the CLI still works (init succeeds).

## Plan

## Rollback

git revert; lazy-import is behavior-preserving when yaml is installed.

## Journal

- 2026-06-14T23:21:17Z [implementation] — Fresh-clone smoke of published v1.5.0 found: every CLI command crashes on clean install with ModuleNotFoundError: yaml (the .tausik/venv lacks pyyaml; project.py imports cmd_renar→project_cli_renar→renar_conformance/export with module-level import yaml). Fixed: lazy yaml in all 3 (project_cli_renar._existing_version, renar_conformance._require_yaml() used by render_yaml, renar_export._frontmatter). render_yaml/export degrade with a clear 'pip install pyyaml' RuntimeError when absent; core CLI loads stdlib-only. AST guard test (test_no_hard_yaml_import) for the 3 modules. Scanned all scripts/ — yaml was the ONLY hard third-party import. Validated end-to-end: overlaid fix on the broken clone → init + status now work (venv without yaml). full mypy/ruff clean (210).
- 2026-06-14T23:21:44Z [implementation] — AC verified: 1. ✓ no module-level import yaml in project_cli_renar/renar_conformance/renar_export — test_no_hard_yaml_import (AST, 3 params). 2. ✓ core CLI imports without yaml — proven by sys.modules['yaml']=None import of all 3 + clone init/status working. 3. ✓ render_yaml/_frontmatter call _require_yaml() → clear 'pip install pyyaml' RuntimeError when absent, other commands unaffected. 4. ✓ AST guard test (AC4). 5. ✓ fresh-clone smoke: overlaid fix on broken v1.5.0 clone → `tausik init` + `tausik status` succeed (venv without yaml). 6. ✓ ruff+mypy clean (210); 98 renar tests still pass with yaml present; files<400. Negative: yaml-absent → renar emit raises actionable RuntimeError, init still succeeds. Root cause (category: dependency): module-level import of an optional dep (PyYAML) in a CLI-reachable module broke the stdlib-only core CLI on clean install. Prevention: lazy imports + AST guard test + fresh-clone smoke in release checklist.
