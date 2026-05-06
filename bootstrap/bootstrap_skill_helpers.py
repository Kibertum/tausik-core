"""TAUSIK bootstrap — skill-specific helpers.

Frontmatter parsing/validation, skill source resolution, on-demand stub
generation, and registry loading. Extracted from bootstrap_copy.py to
keep that module under the 400-line filesize gate (v14b polish Phase B).

Re-exported via bootstrap_copy so existing external imports keep working
(skill_profile.py, tests/test_bootstrap_frontmatter.py).
"""

from __future__ import annotations

import os
import re
from typing import Any

# --- Skill frontmatter validation ---

VALID_CONTEXT = {"inline", "fork"}
VALID_EFFORT = {"fast", "medium", "slow"}


def parse_skill_frontmatter(skill_md_path: str) -> dict[str, str] | None:
    """Parse YAML frontmatter from a SKILL.md file. Returns dict or None.

    Simple parser — not a full YAML parser.
    Handles: key: value, key: "value", key: 'value'
    Does NOT handle: multi-line values, nested structures, anchors.
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


def validate_skill_frontmatter(skill_name: str, fields: dict[str, str]) -> list[str]:
    """Validate optional frontmatter fields (context, effort, paths).

    Required fields (name, description) are not checked here.
    Returns list of warnings (empty = OK).
    """
    warnings: list[str] = []
    ctx = fields.get("context")
    if ctx and ctx not in VALID_CONTEXT:
        warnings.append(
            f"skill '{skill_name}': invalid context '{ctx}' "
            f"(expected: {', '.join(sorted(VALID_CONTEXT))})"
        )
    effort = fields.get("effort")
    if effort and effort not in VALID_EFFORT:
        warnings.append(
            f"skill '{skill_name}': invalid effort '{effort}' "
            f"(expected: {', '.join(sorted(VALID_EFFORT))})"
        )
    paths = fields.get("paths")
    if paths is not None and not paths:
        warnings.append(f"skill '{skill_name}': 'paths' is empty")
    return warnings


def _resolve_skill(
    name: str,
    builtin_dir: str,
    adjacent_dir: str | None,
    vendor_skills: dict[str, str] | None,
) -> tuple[str | None, str]:
    """Resolve skill source by chain: builtin → adjacent → vendor.

    Returns (path, source_type) or (None, "missing").
    """
    # 1. Built-in (core repo harness/skills/)
    p = os.path.join(builtin_dir, name)
    if os.path.isdir(p):
        return p, "builtin"
    # 2. Adjacent skills repo (../skills-official/ or ../skills/)
    if adjacent_dir:
        p = os.path.join(adjacent_dir, name)
        if os.path.isdir(p):
            return p, "official"
    # 3. Vendor (downloaded via skills.json)
    if vendor_skills and name in vendor_skills:
        return vendor_skills[name], "vendor"
    return None, "missing"


def _generate_stub(name: str, registry: dict[str, Any] | None) -> str:
    """Generate a lightweight SKILL.md stub for on-demand loading.

    Stubs contain only frontmatter so the IDE registers the skill name and
    trigger description without loading the full algorithm into context.
    """
    meta = (registry or {}).get(name, {})
    desc = meta.get("description", f"Official skill '{name}' (not yet loaded)")
    context = meta.get("context", "inline")
    effort = meta.get("effort", "medium")
    tags = ", ".join(meta.get("tags", []))
    env_hint = ""
    if meta.get("env_required"):
        env_hint = f"\nRequires env: {', '.join(meta['env_required'])}"
    return (
        f"---\nname: {name}\n"
        f'description: "{desc}"\n'
        f"context: {context}\n"
        f"effort: {effort}\n"
        f"source: official\n---\n\n"
        f"# /{name} — on-demand skill\n\n"
        f"This skill is available but not loaded into context yet.\n"
        f"Run `.tausik/tausik skill activate {name}` or use "
        f"`tausik_skill_activate` MCP tool to load the full version.\n"
        f"{env_hint}\n"
        f"Tags: {tags}\n"
    )


def _load_registry(adjacent_dir: str | None) -> dict[str, Any] | None:
    """Load registry.json from adjacent skills directory."""
    if not adjacent_dir:
        return None
    reg_path = os.path.join(adjacent_dir, "registry.json")
    if not os.path.isfile(reg_path):
        return None
    try:
        import json

        with open(reg_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("skills", {})
    except (OSError, ValueError):
        return None
