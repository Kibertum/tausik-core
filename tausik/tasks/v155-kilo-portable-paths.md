---
slug: v155-kilo-portable-paths
title: "Rename-proof Kilo config via ${workspaceFolder}"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "bootstrap/bootstrap_kilo.py, tests/test_bootstrap_kilo.py"
scope_exclude: "bootstrap_generate.py/bootstrap_qwen.py (framework-wide = separate task), scripts/*"
relevant_files:
  - "bootstrap/bootstrap_kilo.py"
  - "tests/test_bootstrap_kilo.py"
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T08:52:10Z"
---

## Goal

Make the generated Kilo MCP config survive a project-folder rename: emit ${workspaceFolder}-relative paths for servers under the project and for --project, instead of absolute paths. Addresses the user complaint that renaming the folder breaks the framework (Kilo supports ${workspaceFolder}).

## Acceptance Criteria

1. When the resolved server.py is UNDER project_dir, generate_kilo_config emits its path as ${workspaceFolder}/<relpath> (forward-slashed), not absolute. 2. The --project arg is always ${workspaceFolder}. 3. When the server is OUTSIDE project_dir (external lib), the absolute path is kept (project rename doesn't affect it) — documented. 4. Existing tests updated; new test asserts no absolute project path leaks for an in-project server + a rename simulation (move dir, config still resolves via ${workspaceFolder}). 5. ruff+mypy clean. NEGATIVE: a server resolved from an external lib_dir still works (absolute path retained, no ${workspaceFolder} misapplied); python_exe untouched (separate concern, noted).

## Plan

## Rollback

git checkout bootstrap/bootstrap_kilo.py tests/test_bootstrap_kilo.py — isolated to the Kilo generator.

## Journal

- 2026-06-19T08:52:09Z [implementation] — AC1 ✓ in-project server emitted as ${workspaceFolder}/<relpath> — tests/test_bootstrap_kilo.py::test_in_project_server_is_rename_proof. AC2 ✓ --project always ${workspaceFolder} (same test + ::test_external_lib_server_stays_absolute). AC3 ✓ external lib server keeps absolute path — ::test_external_lib_server_stays_absolute. AC4 ✓ 11 kilo tests pass incl. rename-proofing; docs (EN+RU) updated to ${workspaceFolder} example. AC5 ✓ ruff+mypy clean. NEGATIVE ✓ external lib absolute retained (no ${workspaceFolder} misapplied), python_exe untouched (noted as separate concern). Framework-wide assessment → deferred task v156-portable-paths-all-ides (per-IDE verification needed, regression risk). Domain: renaming the Kilo project folder no longer breaks the MCP config — directly resolves the user complaint for the Kilo path.
