---
slug: file-size-limit-400-lines
title: "File size limit 400 lines"
type: convention
tags:
  - convention
  - files
task: null
edges: []
---

Max 400 lines per file. If exceeding — decompose into mixin, sub-module, re-export from __init__.py. Exceptions: tests, generated code. Check with wc -l after creating/modifying.
