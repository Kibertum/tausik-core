"""v1.4 artifact taxonomy for Shared Brain writes (documentation + guard rails).

Canonical kinds for *optional* MCP field `artifact_taxonomy_kind` on
`brain_store_pattern` / `brain_store_gotcha`:
  - artifact — umbrella knowledge unit (conceptual bundle; may map to several DB rows)
  - pattern  — reusable recipe / best practice → Notion `patterns` table
  - snippet  — minimal excerpt (code/config) suitable for reuse; v1 stored as a pattern
    row with taxonomy `snippet` until a dedicated DB exists

Notion property support for the field is deferred; the value is stripped before
`build_properties_*` and used for validation / future sync only.
"""

from __future__ import annotations

from typing import Any

ALLOWED_ARTIFACT_TAXONOMY_KINDS = frozenset({"artifact", "pattern", "snippet"})
_TAXONOMY_CATEGORIES = frozenset({"patterns", "gotchas"})


def validate_artifact_taxonomy_for_store(
    category: str, fields: dict[str, Any], cfg: dict[str, Any]
) -> tuple[bool, str | None]:
    """Return (True, None) or (False, error_message).

    Rules:
      * For `patterns` / `gotchas`, if `brain.require_artifact_taxonomy_kind` is true,
        `artifact_taxonomy_kind` must be present, non-empty, and one of ALLOWED_*.
      * If the key is present with any non-empty value, it must be a valid kind
        (even when strict mode is off) — catches typos early.
      * Empty / whitespace-only values are always rejected when the key is present.
    """
    if category not in _TAXONOMY_CATEGORIES:
        return True, None

    strict = bool(cfg.get("require_artifact_taxonomy_kind"))
    raw = fields.get("artifact_taxonomy_kind")

    if raw is None:
        if strict:
            return (
                False,
                "artifact_taxonomy_kind is required for this category "
                "(set brain.require_artifact_taxonomy_kind in config to false to opt out). "
                f"Allowed: {', '.join(sorted(ALLOWED_ARTIFACT_TAXONOMY_KINDS))}.",
            )
        return True, None

    if not isinstance(raw, str):
        return False, "artifact_taxonomy_kind must be a string"

    norm = raw.strip().lower()
    if not norm:
        return False, "artifact_taxonomy_kind cannot be empty or whitespace"

    if norm not in ALLOWED_ARTIFACT_TAXONOMY_KINDS:
        return (
            False,
            f"invalid artifact_taxonomy_kind {raw!r}; allowed: "
            f"{', '.join(sorted(ALLOWED_ARTIFACT_TAXONOMY_KINDS))}",
        )

    return True, None
