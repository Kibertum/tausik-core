---
slug: drift-checks-numeric-word-boundary-compare-never-substring
title: "Drift checks: numeric/word-boundary compare, never substring"
type: gotcha
tags:
  - aidd
  - drift
  - false-ok
  - validation
task: v15-aidd-validate-cmd
edges: []
---

When a checker compares a CLAIMED token against repo reality (versions, tool names, framework names — e.g. `tausik aidd validate`), naive substring membership causes silent false-OK: `'3.1' in '>=3.11'` is True; `'flake8' in 'flake8-bugbear'` is True; detected `'ava'` substring-matches a `'javascript'` claim. Fix: (1) versions → parse to (major,minor) int tuples and compare numerically (_minor_version in project_cli_aidd_validate.py); (2) tool/framework names → word-boundary regex `\b<name>\b` for claim extraction, and for dependency/requirement presence require line-start `^<name>(?=$|[=<>!~;\[\s])` or parse package.json dep KEYS (not raw text). False-OK is worse than false-drift here — it hides real config drift. Surfaced by adversarial review on a separate model.
