---
slug: enabling-a-global-ruff-rule-ci-lints-a-subset-ruff-check
title: "Enabling a global ruff rule: CI lints a subset, `ruff check .` lints more"
type: gotcha
tags:
  - ble001
  - ci
  - lint-scope
  - ruff
task: v15p-ble001-harness-annotate
edges: []
---

CI runs `ruff check scripts/ tests/ bootstrap/` (explicit paths), but a developer's `ruff check .` traverses the whole repo (minus .gitignore → skips .claude/.tausik) INCLUDING harness/**/mcp (committed MCP source copies, claude+cursor). When you enable a repo-wide rule via [tool.ruff.lint] extend-select, annotating only the CI paths leaves `ruff check .` red (harness flagged) even though CI is green. Fix: annotate the WHOLE tree (incl harness), not just CI scope — do NOT mask with extend-exclude (that hides real sites). Guard with a test that runs `ruff check --select <CODE> .` (whole tree), not the CI subset. Surfaced enabling BLE001: 133 CI-scope sites annotated but 64 harness sites left `ruff check .` with 64 errors. Pairs with [[enabling-a-new-ruff-lint-over-many-legacy-sites-annotate-then-flip-atomic-safe]] (memory #169).
