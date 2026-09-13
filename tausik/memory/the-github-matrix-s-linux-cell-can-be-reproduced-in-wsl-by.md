---
slug: the-github-matrix-s-linux-cell-can-be-reproduced-in-wsl-by
title: "The GitHub matrix's Linux cell can be reproduced in WSL by the workflow's own steps before any push"
type: gotcha
tags:
  - "ci,linux,wsl,matrix,release"
task: null
edges: []
---

Session #260: wsl -d Ubuntu-24.04, clone from /mnt/d, venv, pip install pytest pytest-xdist ruff mypy bandit + requirements.txt, bootstrap --no-detect --ide all, gen_doc_constants --check --skip-test-count, ruff, pytest tests/ (fast lane). Found two Linux-only reds on a tree that was 0-failed on Windows: a path spelling only a case-folding filesystem equates, and a wall-clock bar the WSL disk's fsync cannot meet. Run it before calling a tree matrix-ready; ~6 min.
