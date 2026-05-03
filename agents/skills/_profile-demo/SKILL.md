---
name: profile-demo
description: "Reference skill for variants/ (underscore prefix — not deployed by bootstrap)."
profile_fallback: claude
---

# Profile demo — shared core

This skill documents the **variants/** layout. All hosts see this body.

## Algorithm

1. Ship one **SKILL.md** with shared steps.
2. Put host-specific deltas in **`variants/<profile>.md`** (markdown fragments, no required frontmatter).
3. At resolve time, pass the host profile (e.g. `claude`, `codex`). If the variant file is missing, **profile_fallback** in frontmatter selects another variant; if still missing, only this base file is used — **no crash**.

## Gotchas

- Underscore-prefixed skill dirs are **reference-only** — bootstrap skips them; hosts never see this as an installable slash skill.
- Without **`profile_fallback`**, an unknown profile yields **no overlay** (base markdown only); test your slug normalization against **variants/** filenames.
- Keep overlays short: large duplicates belong in the shared body above, not in **variants/**.
