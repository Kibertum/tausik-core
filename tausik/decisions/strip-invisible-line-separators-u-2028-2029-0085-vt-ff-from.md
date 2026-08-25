---
slug: strip-invisible-line-separators-u-2028-2029-0085-vt-ff-from
task: brain-review2-hardening-v2
date: "2026-04-24"
edges: []
---

## Decision

Strip invisible line separators (U+2028/2029/0085/VT/FF) from transcript text before anchor-matching, do NOT convert them to \n

## Rationale

Attacker embeds U+2028 between letters of inline prose so splitlines() produces a "line" containing just the bypass marker — visually the text is still one sentence, so the user doesn't see what they're "activating". Converting U+2028→\n preserves this attack; stripping collapses the prose back to a real single line where the marker is merely a substring and fails the anchor check. Legitimate content never relies on U+2028 as a paragraph break.
