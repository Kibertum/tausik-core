---
slug: derived-file-export-views-must-be-date-free-to-keep-check
title: "Derived file-export views must be date-free to keep --check stable"
type: pattern
tags:
  - determinism
  - drift-gate
  - export
  - phase-0
  - renar
task: renar-file-export
edges: []
---

When serializing DB state to a git-tracked derived tree with a `--check` drift gate (e.g. `tausik renar export`), exclude write-time volatile metadata (assessment-date, next-assessment-due, manifest-id, generation timestamps) from the exported files. Otherwise --check drifts every day even with an unchanged DB, producing spurious churn and CI failures. renar_export._conformance_doc derives level/signals/clauses directly via renar_conformance.gather_signals+eval_mandatory_clauses+infer_level (NOT the dated generate()/manifest) — the dated RENAR-CONFORMANCE.yaml manifest stays a separate write-time artifact. Determinism recipe: slug-sorted iteration, yaml.safe_dump(sort_keys=True), id-ordered child lists, role/target-sorted nested lists, newline="\n". The export OWNS *.md under the tree (deletion reconciliation scoped to MANAGED_SUFFIX so pointing --out at a populated dir can't nuke unrelated files).
