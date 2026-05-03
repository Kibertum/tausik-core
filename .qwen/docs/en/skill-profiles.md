**English** | [Русский](../ru/skill-profiles.md)

# Skill profiles and `variants/` (v1.4)

TAUSIK skills are normally a single **`SKILL.md`**. When behaviour differs by host (Claude vs Codex vs GPT wrapper) **without copying the whole skill**, use optional **profile overlays**.

## Layout

```
agents/skills/<skill-name>/
  SKILL.md              # Shared instructions + YAML frontmatter
  variants/
    claude.md           # Fragment appended when profile resolves to claude
    codex.md            # Fragment for codex
```

## Frontmatter (optional)

| Field | Meaning |
|--------|---------|
| `profile_fallback` | If the requested profile has **no** `variants/<profile>.md`, try this profile once for overlay lookup (slug: lowercase, `a-z0-9-`). |

Existing TAUSIK fields (`name`, `description`, `context`, `effort`, …) stay unchanged.

## Resolution algorithm

1. Load **`SKILL.md`** as the base document (including its frontmatter).
2. If no profile is requested → return the base only.
3. If **`variants/<requested>.md`** exists → append its body after the base (separator comment `<!-- tausik-profile:<slug> -->`).
4. Else if **`profile_fallback`** is set and **`variants/<fallback>.md`** exists → append that overlay (same separator).
5. Else → return **base only** (unknown profile is **not** an error).

Reference implementation: `scripts/skill_profile.py` (`merge_skill_markdown`, `resolve_variant_overlay`).

## Example

See **`agents/skills/_profile-demo/`** (reference layout — not deployed to IDE; prefixed with `_`): shared core plus **`variants/claude.md`** and **`variants/codex.md`**. Requesting profile `gpt` with `profile_fallback: claude` uses the Claude overlay when no `variants/gpt.md` exists.
