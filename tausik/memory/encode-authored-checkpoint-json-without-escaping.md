---
slug: encode-authored-checkpoint-json-without-escaping
title: "Encode authored checkpoint JSON without escaping apostrophes inside Python source"
type: dead_end
tags:
  - checkpoint
  - powershell
task: r111-economy-hardening-acceptance
edges: []
---

Approach: Encode authored checkpoint JSON without escaping apostrophes inside Python source
Reason: JavaScript encodeURIComponent leaves apostrophes unchanged, which terminated the Python string; encode apostrophes explicitly or avoid them.
