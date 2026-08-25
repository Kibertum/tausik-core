---
slug: bypass-markers-require-anchored-line-outside-all-code
title: "Bypass markers: require anchored line outside all code contexts"
type: pattern
tags:
  - bypass
  - hooks
  - security
task: null
edges: []
---

When a hook supports a "bypass marker" (e.g. `confirm: cross-project`, `refresh: web_cache`), the match MUST require ALL of:
1. Marker on a line by itself (stripped whitespace equals marker)
2. Line outside any fenced code block (``` or ~~~)
3. Line is NOT 4+ space / tab indented (markdown indented code)
4. Invisible separators (U+2028/2029/0085/VT/FF) stripped before line split — NOT converted to \n

A naive `marker in prompt.lower()` lets the user accidentally trigger bypass by quoting the hook's own error text. Fenced code skip alone is insufficient: tilde fences and indented-code blocks both also render as code in agents/UIs. Invisible line separators let an attacker smuggle the marker into inline prose.

Implemented in scripts/hooks/_common.py as marker_present_anchored(). Reused by memory_pretool_block and brain_search_proactive.
