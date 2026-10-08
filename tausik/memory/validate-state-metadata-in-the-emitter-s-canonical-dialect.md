---
slug: validate-state-metadata-in-the-emitter-s-canonical-dialect
title: "Validate state metadata in the emitter's canonical dialect before apply"
type: pattern
tags:
  - assurance
  - state-import
  - validation
task: validate-assurance-metadata-at-state-import
edges: []
---

State import separates parse from apply, so typed metadata must be decoded exactly as state_export emits it and validated during parse_tree. This preserves whole-batch refusal before any transaction while keeping the restricted YAML dialect stable.
