"""Resolve TAUSIK skill markdown for IDE + model profiles (variants/).

Two independent axes (B8-pre axis decision):
- IDE overlay:   <skill>/variants/ide/<ide>.md     (claude/cursor/qwen/codex)
- Model overlay: <skill>/variants/model/<model>.md (opus/sonnet/gpt-5/...)

Backward compat: legacy flat layout <skill>/variants/<slug>.md still works
when the new ide/ + model/ subdirs are absent — caller passes a single
``requested_profile`` and the resolver walks the flat path.
"""

from __future__ import annotations

import os
import re
from typing import Any, Final


def parse_skill_frontmatter(skill_md_path: str) -> dict[str, str] | None:
    """Local copy of bootstrap.bootstrap_skill_helpers.parse_skill_frontmatter.

    Duplicated intentionally so scripts/ has no dependency on bootstrap/
    (the latter is absent from .claude/scripts/ runtime). Simple parser —
    handles `key: value`, `key: "value"`, `key: 'value'` only.
    """
    try:
        with open(skill_md_path, encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return None
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return None
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def normalize_profile_slug(raw: str) -> str:
    """Lowercase slug: letters, digits, hyphen only."""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


_PROFILE_MARKER: Final = "<!-- tausik-profile:"


def _strip_existing_overlays(text: str) -> str:
    """Return text with everything from the first profile marker onward removed.

    Lets ``merge_skill_markdown`` re-merge an already-merged SKILL.md without
    accumulating overlay sections across repeated rebuilds (idempotency).
    """
    idx = text.find(_PROFILE_MARKER)
    if idx == -1:
        return text
    return text[:idx].rstrip() + "\n"


def _read_overlay(skill_dir: str, axis: str, slug: str) -> str | None:
    """Return overlay text from variants/<axis>/<slug>.md or None if missing."""
    if not slug:
        return None
    path = os.path.join(skill_dir, "variants", axis, f"{slug}.md")
    if os.path.isfile(path):
        return read_text(path)
    return None


def resolve_variant_overlay(
    skill_dir: str, requested_profile: str | None
) -> tuple[str | None, str]:
    """LEGACY flat-layout resolver. Returns (overlay_text, resolved_slug).

    Used by callers passing a single ``requested_profile`` against the old
    flat ``variants/<slug>.md`` layout. New callers should pass ide/model
    explicitly to ``merge_skill_markdown``.

    If ``requested_profile`` is empty, no overlay. If the variant file is missing,
    try ``profile_fallback`` from ``SKILL.md`` frontmatter once. Unknown profile
    with no fallback file -> (None, "") -- caller keeps base SKILL.md only
    (no exception).
    """
    if not requested_profile or not str(requested_profile).strip():
        return None, ""

    slug = normalize_profile_slug(str(requested_profile))
    if not slug:
        return None, ""

    def _flat_variant_path(name: str) -> str:
        return os.path.join(skill_dir, "variants", f"{name}.md")

    vp = _flat_variant_path(slug)
    if os.path.isfile(vp):
        return read_text(vp), slug

    fm: dict[str, Any] = parse_skill_frontmatter(os.path.join(skill_dir, "SKILL.md")) or {}
    fb = (fm.get("profile_fallback") or "").strip()
    if fb:
        fb_slug = normalize_profile_slug(fb)
        if fb_slug and fb_slug != slug:
            vp2 = _flat_variant_path(fb_slug)
            if os.path.isfile(vp2):
                return read_text(vp2), fb_slug

    return None, ""


def merge_skill_markdown(
    skill_dir: str,
    requested_profile: str | None = None,
    *,
    ide: str | None = None,
    model: str | None = None,
) -> str:
    """Full SKILL.md plus optional IDE + model overlays.

    Resolution priority:
      1. If ``ide`` or ``model`` is set, use the two-axis layout
         (variants/ide/<ide>.md, variants/model/<model>.md). Either or both
         may be missing — silently skipped.
      2. Else if ``requested_profile`` is set, use the legacy flat layout
         (variants/<slug>.md) for backward compatibility with external
         skill repos that haven't migrated.
      3. Else return base SKILL.md unchanged.

    Two-axis merge order: base + IDE overlay + model overlay. The order
    is deliberate — IDE constraints should be set first (how the host
    invokes tools), then model style overlays nudge tone/verbosity.
    """
    base_path = os.path.join(skill_dir, "SKILL.md")
    base = _strip_existing_overlays(read_text(base_path))

    if ide is not None or model is not None:
        ide_slug = normalize_profile_slug(ide) if ide else ""
        model_slug = normalize_profile_slug(model) if model else ""
        ide_overlay = _read_overlay(skill_dir, "ide", ide_slug) if ide_slug else None
        model_overlay = _read_overlay(skill_dir, "model", model_slug) if model_slug else None
        out = base.rstrip()
        if ide_overlay:
            out += f"\n\n<!-- tausik-profile:ide={ide_slug} -->\n\n" + ide_overlay.strip()
        if model_overlay:
            out += f"\n\n<!-- tausik-profile:model={model_slug} -->\n\n" + model_overlay.strip()
        return out + "\n"

    overlay, resolved = resolve_variant_overlay(skill_dir, requested_profile)
    if overlay is None:
        return base
    sep = f"\n\n<!-- tausik-profile:{resolved} -->\n\n"
    return base.rstrip() + sep + overlay.strip() + "\n"
