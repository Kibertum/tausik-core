---
slug: converting-u-2028-u-2029-to-n-before-splitting-in-marker
title: "Converting U+2028/U+2029 to \\n before splitting in marker anchor check"
type: dead_end
tags:
  - hooks
  - security
  - unicode
task: null
edges: []
---

Approach: Converting U+2028/U+2029 to \n before splitting in marker anchor check
Reason: Attack vector of U+2028/2029 is EXACTLY that splitlines() treats them as line breaks while they're invisible in rendered prose. Converting them to \n preserves the attack — the marker becomes a standalone "line" and triggers bypass. Fix: strip the separators entirely (sub to '' not '\n'), collapsing attacker's fake standalone marker back to substring in inline prose. Legitimate content never relies on U+2028 as a paragraph break.
