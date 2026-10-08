---
slug: keep-answer-shape-reconciliation-inline-in-bootstrap
title: "Keep answer-shape reconciliation inline in bootstrap_templates.py"
type: dead_end
tags:
  - answer-shape
  - bootstrap
  - filesize
task: ship-answer-shape-into-existing-consumer-rules
edges: []
---

Approach: Keep answer-shape reconciliation inline in bootstrap_templates.py
Reason: The first scoped verify #3357 enforced the 500-line module cap at 515 lines; the byte-preserving mechanism was extracted to bootstrap_rules_upgrade.py and the canonical template returned to 484 lines.
