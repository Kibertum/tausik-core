---
slug: v155-kilo-python-portable-gitignore
title: "Dogfood fixes: Kilo python_exe portable + gitignore .kilo/.kilocode"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: simple
role: developer
stack: python
tier: light
call_budget: 20
defect_of: v155-kilo-portable-paths
scope: "bootstrap/bootstrap_kilo.py, .gitignore, tests/test_bootstrap_kilo.py"
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_kilo.py"
  - ".gitignore"
  - "tests/test_bootstrap_kilo.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T09:29:38Z"
---

## Goal

Self-bootstrap revealed: (1) Kilo MCP command's python_exe stayed absolute (_p instead of _portable_path) — an in-project venv breaks on rename; claude/cursor already handle it. (2) Generated .kilo/ and .kilocode/ are not gitignored like sibling IDE dirs (.claude/.cursor/.qwen). Fix both.

## Acceptance Criteria

1. bootstrap_kilo._build_mcp_servers emits python_exe via _portable_path so an in-project venv becomes ${workspaceFolder}/.tausik/venv/... (matches claude/cursor). 2. .gitignore ignores .kilo/ and .kilocode/. 3. New test asserts an in-project venv python in the Kilo config is ${workspaceFolder}-relative. 4. Re-running self-bootstrap produces a Kilo config with NO absolute project path anywhere. NEGATIVE: a bare 'python' (no venv) stays 'python' (not rewritten); an external/system python stays absolute.

## Plan

## Rollback

git checkout bootstrap/bootstrap_kilo.py .gitignore tests/test_bootstrap_kilo.py

## Journal

- 2026-06-19T09:29:10Z [implementation] — Root cause (logic-error): when adding ${workspaceFolder} portability to bootstrap_kilo, I rewrote the server path via _portable_path but left python_exe on the old _p() (forward-slash only) — so an in-project venv stayed absolute and broke on folder rename. claude/cursor generators (edited separately) did apply it to python, so the miss was Kilo-specific inconsistency. Also .kilo/.kilocode were never added to .gitignore alongside sibling IDE dirs. Prevention: when a path-portability helper is introduced, apply it to EVERY path emitted (interpreter + script + project arg), and dogfood the generator (self-bootstrap + grep for the absolute project path) — unit tests used external paths so they didn't catch the in-project venv case. Caught only by self-bootstrap.
- 2026-06-19T09:29:19Z [implementation] — AC1 ✓ python_exe via _portable_path — tests/test_bootstrap_kilo.py::test_in_project_venv_python_is_portable. AC2 ✓ .gitignore adds .kilo/ + .kilocode/ (git check-ignore confirms both ignored). AC3 ✓ same test asserts ${workspaceFolder}/.tausik/venv/Scripts/python.exe. AC4 ✓ DOGFOOD: self-bootstrap --ide kilo → grep '[вычеркнуто: local-path]' in .kilo/kilo.jsonc = 0 (no absolute project path); --ide claude → .mcp.json also 0, hooks = 'python ${CLAUDE_PROJECT_DIR}/scripts/hooks/...'. NEGATIVE ✓ ::test_bare_python_stays_bare (no venv → 'python'); ::test_external_lib_server_stays_absolute (external stays absolute). 13 kilo tests pass, ruff+mypy clean. Root cause (logic-error) logged. Domain: TAUSIK bootstrapping itself now produces a fully rename-proof config — verified on the real repo.
- 2026-06-19T09:29:37Z [implementation] — AC1-4 + negatives verified (prior log): in-project venv python now ${workspaceFolder}-relative; .kilo/.kilocode gitignored; DOGFOOD self-bootstrap → 0 absolute project paths in .kilo/kilo.jsonc AND .mcp.json; bare python + external stay correct. 13 kilo tests pass. Knowledge: gotcha Memory #180. Root cause (logic-error): portability helper applied to server path but not python_exe in Kilo only; unit tests used external paths so missed the in-project venv — caught only by dogfooding.
