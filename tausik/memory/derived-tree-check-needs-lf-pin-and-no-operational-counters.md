---
slug: derived-tree-check-needs-lf-pin-and-no-operational-counters
title: "Derived-tree --check needs LF pin AND no operational counters"
type: gotcha
tags:
  - determinism
  - drift-gate
  - eol
  - export
  - gitattributes
  - renar
task: renar-tree-gitattributes-lf
edges: []
---

Two non-obvious determinism holes break a `--check` drift gate over a git-tracked generated tree, neither visible in static-DB unit tests: (1) core.autocrlf=true + no .gitattributes → git checks out the generated *.md as CRLF while the generator writes LF (newline='\n') → false 'changed' drift on fresh clones. Fix: scope a .gitattributes rule (e.g. `renar/** text eol=lf`); do NOT use a global `* eol=lf` (reformats unrelated tracked files). (2) Embedding live operational counters (verification_runs/memory_edges/reasoning_tasks counts from gather_signals raw-counts) into the exported view churns the tree on every verify/memory op. Fix: export only artifact-derived state (level/signals/clauses), never raw operational counters. Test the second with a regression that inserts a verification_run between two builds and asserts the exported file is byte-identical. See [[derived-views-must-be-date-free]] (#162) — same family: exclude anything that moves for reasons unrelated to the artifacts.
