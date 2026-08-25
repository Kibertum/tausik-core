---
slug: after-editing-scripts-bootstrap-before-dogfood-via-tausik
title: "After editing scripts/* — bootstrap before dogfood via .tausik/tausik CLI"
type: convention
tags:
  - bootstrap
  - dogfood
  - workflow
task: null
edges: []
---

.tausik/tausik wrapper invokes .claude/scripts/* (generated copy by bootstrap.py), NOT root scripts/*. Source-only edits in scripts/ are invisible to the CLI until `python bootstrap/bootstrap.py` regenerates the copy. Symptom: CLI keeps emitting old error messages or behaviors after a code fix. Always: edit scripts/ → bootstrap → dogfood. Same applies to harness/* (bootstrap copies it into .claude/, .cursor/, .qwen/). Direct python imports from tests/ pick up source changes immediately because pytest uses sys.path → scripts/ — only the wrapper layer needs regen.
