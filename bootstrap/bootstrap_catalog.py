"""TAUSIK bootstrap — skill catalog generator."""

from __future__ import annotations

import os
from typing import Any


def generate_skill_catalog(
    target_dir: str,
    manifest: dict[str, Any],
    installed_skills: list[str],
    vendor_dir: str | None = None,
) -> None:
    """Generate skill-catalog.md — lists available skills for agent context.

    Three-level system to minimize token usage:
    - ACTIVE: in {ide_dir}/skills/, loaded into system prompt every message
    - VENDORED: downloaded to .tausik/vendor/, zero tokens, instant activation
    - AVAILABLE: in skills.json but not downloaded yet, needs --update-deps
    """
    external = manifest.get("external_skills", {})
    if not external:
        return

    # Derive IDE dir name from target_dir (e.g. ".claude", ".qwen", ".cursor")
    ide_dir = os.path.basename(target_dir)

    lines = [
        "# External Skill Catalog",
        "",
        "This file is NOT loaded into every message. Agent reads it on-demand",
        "when user request doesn't match installed skills.",
        "",
        "## Activation",
        f"To activate a VENDORED skill: copy from `.tausik/vendor/{{name}}/{{skill}}/`",
        f"to `{ide_dir}/skills/{{skill}}/` — it becomes available immediately.",
        f"To deactivate: delete from `{ide_dir}/skills/{{skill}}/`.",
        "",
    ]

    for name, spec in external.items():
        desc = spec.get("description", "No description")
        triggers = spec.get("triggers", [])
        repo = spec.get("repo", "")
        ref = spec.get("ref", "main")

        is_active = any(name in s or s.startswith(name) for s in installed_skills)
        is_vendored = False
        if vendor_dir:
            vendor_path = os.path.join(vendor_dir, name)
            is_vendored = os.path.isdir(vendor_path)

        if is_active:
            status = "ACTIVE"
        elif is_vendored:
            status = "VENDORED"
        else:
            status = "AVAILABLE"

        lines.append(f"## {name} [{status}]")
        lines.append(f"{desc}")
        lines.append(f"Source: {repo}@{ref}")
        if triggers:
            lines.append(f"Triggers: {', '.join(triggers)}")
        if status == "VENDORED":
            lines.append(
                f"Activate: `cp -r .tausik/vendor/{name}/{{skill}}/ {ide_dir}/skills/{{skill}}/`"
            )
        elif status == "AVAILABLE":
            lines.append(f"Install: run `python bootstrap/bootstrap.py --update-deps`")
        lines.append("")

    lines.extend(
        [
            "---",
            "Agent: when user request matches triggers for a non-ACTIVE skill,",
            f"suggest activation. If VENDORED — copy to {ide_dir}/skills/. If AVAILABLE — run bootstrap.",
            f"On /end or /checkpoint — remove vendor skills from {ide_dir}/skills/ to keep context clean.",
        ]
    )

    catalog_path = os.path.join(target_dir, "references", "skill-catalog.md")
    os.makedirs(os.path.dirname(catalog_path), exist_ok=True)
    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
