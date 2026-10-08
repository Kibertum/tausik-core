---
slug: tausik-gates-json-is-read-by-a-citation-guard-a-node-id
title: "tausik/gates.json is read by a citation guard: a node id written there as an EXAMPLE must exist"
type: gotcha
tags:
  - "gates-json,citation,guard,closure-evidence"
task: null
edges: []
---

Session #257, one hour after memory #699: the closure-evidence comment in tausik/gates.json quoted an invented Class::method as the example of what stays never-existed; tests/test_gate_class_surface.py::test_every_test_gates_json_cites_actually_exists holds every file::node in that file to a real symbol and the full lane went red (1 failed / 10562 passed). Two readers of verbatim node ids: the closure extractor (journals) and the gates.json guard. Name a bad citation by its TASK and a paraphrase in both places.
