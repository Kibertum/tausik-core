---
slug: expensive-answer-guidance-is-conditional-on-prompt-intent
title: "Expensive answer guidance is conditional on prompt intent"
type: pattern
tags:
  - answer-format
  - economy
  - prompt-hook
  - visualization
task: route-explanations-to-smallest-useful-format
edges: []
---

Keep ordinary prompts free of visualization-routing text. On explanation/comparison/visualization intent, reuse UserPromptSubmit to inject one bounded matrix: prose fallback, table for repeated exact mappings, Mermaid for connected structure, HTML/video only on explicit need. No renderer or model call is required.
