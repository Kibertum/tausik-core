---
slug: nfkc-normalization-for-unicode-aware-substring-blocklist
title: "NFKC normalization for unicode-aware substring blocklist matching"
type: dead_end
tags:
  - scrubbing
  - unicode
task: null
edges: []
---

Approach: NFKC normalization for unicode-aware substring blocklist matching
Reason: NFKC keeps precomposed characters composed (e.g. é stays as U+00E9), so a follow-up Mn-category strip finds nothing to remove and 'Café' never normalizes to 'cafe'. Fixed by switching to NFKD, which decomposes é into 'e' + U+0301 combining acute — then Mn strip produces plain ASCII. NFKC is correct for display/comparison of visually-identical strings, but NOT for the "strip-and-compare" pipeline.
