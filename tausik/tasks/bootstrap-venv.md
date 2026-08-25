---
slug: bootstrap-venv
title: "Bootstrap: auto-create venv and install MCP dependencies"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "requirements.txt, bootstrap/bootstrap_venv.py (new), bootstrap/bootstrap.py, bootstrap/bootstrap_generate.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Bootstrap creates .tausik/venv/ with correct Python (>=3.11), installs requirements.txt, and all MCP servers use venv python instead of sys.executable. User's system Python stays clean.

## Acceptance Criteria

1. requirements.txt exists in root with mcp>=1.0.0
2. bootstrap_venv.py: find_python() finds best Python >=3.11 (venv > python3 > python > py -3), shows download instructions if not found
3. bootstrap_venv.py: ensure_venv() creates .tausik/venv/ if missing
4. bootstrap_venv.py: install_requirements() runs pip install -r requirements.txt in venv
5. bootstrap.py calls ensure_venv + install_requirements
6. generate_mcp_json uses venv python path instead of sys.executable
7. Works on Windows and Unix

## Plan

## Rollback

## Journal

- 2026-04-07T21:26:53Z [implementation] — Implementation complete: requirements.txt, bootstrap_venv.py (find_python, ensure_venv, install_requirements), integrated into bootstrap.py + bootstrap_generate.py, docs updated (EN+RU quickstart + agent quickstart), test_bootstrap_venv.py (8 tests pass), all 843 tests pass
- 2026-04-07T21:33:52Z [implementation] — Fixed all subprocess encoding issues across 8 test files: added encoding="utf-8" + errors="replace". Fixed ResourceWarning in test_skills_maturity.py (unclosed file handles). 843 tests pass with -W error (zero warnings).
