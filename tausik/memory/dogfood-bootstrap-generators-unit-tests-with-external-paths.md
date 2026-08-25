---
slug: dogfood-bootstrap-generators-unit-tests-with-external-paths
title: "Dogfood bootstrap generators — unit tests with external paths miss the in-project case"
type: gotcha
tags:
  - bootstrap
  - dogfooding
  - kilo
  - portable-paths
  - v155
task: v155-kilo-python-portable-gitignore
edges: []
---

When making bootstrap-generated paths rename-proof (${workspaceFolder}/${CLAUDE_PROJECT_DIR}), the unit tests passed an EXTERNAL venv python (C:/py/python.exe) and external lib, which portable_path correctly keeps absolute — so they could NOT catch that bootstrap_kilo left python_exe on the old _p() instead of _portable_path(). The real TAUSIK repo has its venv INSIDE the project (.tausik/venv/), so only self-bootstrap (`python bootstrap/bootstrap.py --ide kilo` + `grep -c '<abs-project-path>' .kilo/kilo.jsonc` == 0) exposed the leak. LESSON: for any generator that rewrites paths, (1) apply the helper to EVERY emitted path — interpreter + script + project arg, not just some; (2) dogfood by bootstrapping this repo itself and grepping the output for the absolute project path; (3) add a test with an in-project venv, not only external. Also: new IDE target dirs (.kilo/.kilocode) must be added to .gitignore alongside .claude/.cursor/.qwen — easy to forget.
