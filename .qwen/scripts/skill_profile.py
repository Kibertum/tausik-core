"""Resolve TAUSIK skill markdown for optional host profiles (variants/)."""

from __future__ import annotations

import os
import re
import sys
from typing import Any

_BOOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bootstrap")
if _BOOT not in sys.path:
    sys.path.insert(0, _BOOT)

from bootstrap_copy import parse_skill_frontmatter  # noqa: E402


def normalize_profile_slug(raw: str) -> str:
    """Lowercase slug: letters, digits, hyphen only."""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def resolve_variant_overlay(skill_dir: str, requested_profile: str | None) -> tuple[str | None, str]:
    """Return ``(overlay_text, resolved_slug)``.

    If ``requested_profile`` is empty, no overlay. If the variant file is missing,
    try ``profile_fallback`` from ``SKILL.md`` frontmatter once. Unknown profile
    with no fallback file → ``(None, \"\")`` — caller keeps base ``SKILL.md`` only
    (no exception).
    """
    if not requested_profile or not str(requested_profile).strip():
        return None, ""

    slug = normalize_profile_slug(str(requested_profile))
    if not slug:
        return None, ""

    def _variant_path(name: str) -> str:
        return os.path.join(skill_dir, "variants", f"{name}.md")

    vp = _variant_path(slug)
    if os.path.isfile(vp):
        return read_text(vp), slug

    fm: dict[str, Any] = parse_skill_frontmatter(os.path.join(skill_dir, "SKILL.md")) or {}
    fb = (fm.get("profile_fallback") or "").strip()
    if fb:
        fb_slug = normalize_profile_slug(fb)
        if fb_slug and fb_slug != slug:
            vp2 = _variant_path(fb_slug)
            if os.path.isfile(vp2):
                return read_text(vp2), fb_slug

    return None, ""


def merge_skill_markdown(skill_dir: str, requested_profile: str | None) -> str:
    """Full ``SKILL.md`` plus optional ``variants/<profile>.md`` overlay."""
    base_path = os.path.join(skill_dir, "SKILL.md")
    base = read_text(base_path)
    overlay, resolved = resolve_variant_overlay(skill_dir, requested_profile)
    if overlay is None:
        return base
    sep = f"\n\n<!-- tausik-profile:{resolved} -->\n\n"
    return base.rstrip() + sep + overlay.strip() + "\n"
