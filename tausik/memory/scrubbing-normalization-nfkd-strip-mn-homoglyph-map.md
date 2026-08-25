---
slug: scrubbing-normalization-nfkd-strip-mn-homoglyph-map
title: "Scrubbing normalization: NFKD + strip Mn + homoglyph map + iterated decode"
type: pattern
tags:
  - scrubbing
  - security
  - unicode
task: null
edges: []
---

For substring-based blocklist detection against adversarial input, normalize with:
1. NFKD (not NFKC) — decomposes precomposed chars (é→e+combining acute) so subsequent Mn strip produces plain ASCII
2. Strip category Mn (combining marks)
3. Strip zero-width / bidi chars (U+200B-200F, U+202A-202E, U+2060-2064, U+FEFF)
4. Translate Cyrillic/Greek homoglyphs to Latin (covers ~50 common confusables — не exhaustive)
5. Lowercase
6. Scan both raw-normalized and fully-decoded haystacks (iterate unquote + html.unescape up to 3 rounds or stability)

NFKC alone FAILS the precomposed-char case because it keeps é as U+00E9 (no Mn to strip). Single unquote is bypassed by `%2570rincess`. HTML entity `&#112;` also needs html.unescape.

Implemented in scripts/brain_scrubbing.py._normalize_for_match + _fully_decode. Used for project_names blocklist only (path/email detectors don't need it).
