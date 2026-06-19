"""Pre-merge skills on disk: base + ide overlay + model overlay.

Walks <skills_root>/<slug>/ folders. For each, computes the merged
content (base SKILL.md + variants/ide/<ide>.md + variants/model/<model>.md)
and writes it back to <slug>/SKILL.md ONLY when sha256(merged) differs
from the file already on disk.

Why no-op when content matches:
- Preserves file mtime → git status stays clean.
- Avoids waking up filesystem-watcher tools.
- Keeps prompt cache hits (Anthropic API) hot on repeated session starts.

Public API:
    rebuild_skills(skills_root, ide=None, model=None, *, force=False) -> dict
"""

from __future__ import annotations

import hashlib
import os
from typing import Final

from skill_profile import merge_skill_markdown

_SKILL_BASENAME: Final[str] = "SKILL.md"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _list_skill_dirs(skills_root: str) -> list[str]:
    if not os.path.isdir(skills_root):
        return []
    out: list[str] = []
    for entry in sorted(os.listdir(skills_root)):
        full = os.path.join(skills_root, entry)
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, _SKILL_BASENAME)):
            out.append(full)
    return out


def rebuild_skills(
    skills_root: str,
    ide: str | None = None,
    model: str | None = None,
    *,
    force: bool = False,
) -> dict[str, list[str] | dict[str, str]]:
    """Merge base + overlays for every skill under ``skills_root`` on disk.

    Returns a dict:
        {
            "rebuilt": [skill_slug, ...],
            "skipped": [skill_slug, ...],
            "errors":  {skill_slug: reason, ...},
        }

    Never raises. Errors on individual skills are recorded under
    ``errors`` and processing continues for the rest.
    """
    rebuilt: list[str] = []
    skipped: list[str] = []
    errors: dict[str, str] = {}

    for skill_dir in _list_skill_dirs(skills_root):
        slug = os.path.basename(skill_dir)
        try:
            merged = merge_skill_markdown(skill_dir, ide=ide, model=model)
        except Exception as e:  # noqa: BLE001
            errors[slug] = f"merge failed: {e}"
            continue

        target = os.path.join(skill_dir, _SKILL_BASENAME)
        try:
            with open(target, encoding="utf-8") as f:
                current = f.read()
        except OSError as e:
            errors[slug] = f"read failed: {e}"
            continue

        if not force and _sha256_text(merged) == _sha256_text(current):
            skipped.append(slug)
            continue

        try:
            tmp = target + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(merged)
            os.replace(tmp, target)
            rebuilt.append(slug)
        except OSError as e:
            errors[slug] = f"write failed: {e}"

    return {"rebuilt": rebuilt, "skipped": skipped, "errors": errors}
