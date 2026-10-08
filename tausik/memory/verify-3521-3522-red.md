---
slug: verify-3521-3522-red
title: "Verify #3521/#3522 red"
type: dead_end
tags: []
task: kilo-gate-plugin
edges: []
---

Approach: Verify #3521/#3522 red
Reason: Both gate-found defects, fixed before any green: #3521 — ruff RUF100 unused noqa in the renamed test module, plus the scope-mismatch note that taught us deleted files must not be declared in relevant_files (ruff format cannot format them) while the undeclared file was actually the auto-exported task record; #3522 — cross_model_parity refused task done because kilo had a deployed plugin but no builder in MECHANISM_BUILDERS (the guard working as designed); fixed by adding _build_kilo, harness/kilo/ to the host layer, and two reasoned DECLARED_DIFFERENCES entries.
