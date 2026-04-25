"""TAUSIK bootstrap file copy — skills, scripts, references with IDE awareness."""

from __future__ import annotations

import os
import re
import shutil
import sys
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


def copy_dir(src: str, dst: str) -> None:
    """Copy directory recursively, overwriting destination. Raises on failure."""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(
        src, dst, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc")
    )


def _resolve_skill(
    name: str,
    builtin_dir: str,
    adjacent_dir: str | None,
    vendor_skills: dict[str, str] | None,
) -> tuple[str | None, str]:
    """Resolve skill source by chain: builtin → adjacent → vendor.

    Returns (path, source_type) or (None, "missing").
    """
    # 1. Built-in (core repo agents/skills/)
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


def copy_skills(
    lib_dir: str,
    target_dir: str,
    config: dict[str, Any],
    ide: str,
    vendor_skills: dict[str, str] | None = None,
) -> int:
    """Copy skills to target IDE directory.

    Built-in skills (in agents/skills/) are always copied in full.
    Official and vendor skills are installed as stubs for on-demand loading
    unless explicitly listed in config["installed_skills"].
    Fully activated skills (via skill activate) are copied in full.

    Resolution chain: agents/skills/ → adjacent dir → vendor downloads.
    """
    builtin_dir = os.path.join(lib_dir, "agents", "skills")
    # Adjacent skills repo: ../skills-official/ or ../skills/
    adjacent_dir: str | None = None
    for candidate in ("skills-official", "skills"):
        p = os.path.join(lib_dir, candidate)
        if os.path.isdir(p):
            adjacent_dir = p
            break
    # Also check parent directory (cross-repo dev: tausik/core + tausik/skills)
    if not adjacent_dir:
        parent = os.path.dirname(os.path.abspath(lib_dir))
        for candidate in ("skills-official", "skills"):
            p = os.path.join(parent, candidate)
            if os.path.isdir(p):
                adjacent_dir = p
                break

    registry = _load_registry(adjacent_dir)
    skills_dst = os.path.join(target_dir, "skills")
    os.makedirs(skills_dst, exist_ok=True)
    count = 0
    missing: list[str] = []

    # Validate vendor_activated entries (defense against hand-edited config)
    vendor_activated = [
        v
        for v in config.get("vendor_activated", [])
        if v and ".." not in v and "/" not in v and "\\" not in v
    ]
    # Skills explicitly installed (full copy, not stub)
    installed = set(config.get("installed_skills", []))
    installed.update(vendor_activated)

    # Collect all skill names to process
    all_skills = config.get("core_skills", []) + config.get("extension_skills", [])
    all_skills_with_vendor = list(dict.fromkeys(all_skills + vendor_activated))
    # Also add official skills from registry (as stubs)
    if registry:
        for name in registry:
            if name not in all_skills_with_vendor:
                all_skills_with_vendor.append(name)

    for skill in all_skills_with_vendor:
        src, source_type = _resolve_skill(
            skill, builtin_dir, adjacent_dir, vendor_skills
        )
        dst = os.path.join(skills_dst, skill)

        if source_type == "builtin":
            # Built-in: always full copy
            copy_dir(src, dst)  # type: ignore[arg-type]
            count += 1
        elif src and (skill in installed):
            # Explicitly installed official/vendor: full copy
            copy_dir(src, dst)
            count += 1
        elif src or (registry and skill in registry):
            # Available but not installed: generate stub for on-demand loading
            os.makedirs(dst, exist_ok=True)
            stub_path = os.path.join(dst, "SKILL.md")
            with open(stub_path, "w", encoding="utf-8") as f:
                f.write(_generate_stub(skill, registry))
            count += 1
        else:
            missing.append(skill)

    # Clean up skills that are no longer in the active list
    preserve = set(all_skills_with_vendor)
    if os.path.isdir(skills_dst):
        for existing in os.listdir(skills_dst):
            existing_path = os.path.join(skills_dst, existing)
            if os.path.isdir(existing_path) and existing not in preserve:
                shutil.rmtree(existing_path)

    # Validate frontmatter of all copied skills
    if os.path.isdir(skills_dst):
        for skill_dir_name in sorted(os.listdir(skills_dst)):
            skill_md = os.path.join(skills_dst, skill_dir_name, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            fields = parse_skill_frontmatter(skill_md)
            if fields:
                for warning in validate_skill_frontmatter(skill_dir_name, fields):
                    print(f"  Warning: {warning}", file=sys.stderr)

    if missing:
        print(f"  Warning: skills not found: {', '.join(missing)}", file=sys.stderr)
    return count


def copy_scripts(lib_dir: str, target_dir: str) -> int:
    """Copy scripts/ to target."""
    src = os.path.join(lib_dir, "scripts")
    dst = os.path.join(target_dir, "scripts")
    if not os.path.isdir(src):
        return 0
    copy_dir(src, dst)
    return len([f for f in os.listdir(dst) if f.endswith(".py")])


def copy_mcp(lib_dir: str, target_dir: str, ide: str) -> int:
    """Copy MCP servers from agents/{ide}/mcp/ to target."""
    mcp_src = os.path.join(lib_dir, "agents", ide, "mcp")
    if not os.path.isdir(mcp_src):
        mcp_src = os.path.join(lib_dir, "agents", "claude", "mcp")
    if not os.path.isdir(mcp_src):
        return 0
    mcp_dst = os.path.join(target_dir, "mcp")
    copy_dir(mcp_src, mcp_dst)
    return len(os.listdir(mcp_dst))


def copy_roles(lib_dir: str, target_dir: str, ide: str) -> int:
    """Copy role profiles from agents/roles/ (shared) to target."""
    roles_src = os.path.join(lib_dir, "agents", "roles")
    if not os.path.isdir(roles_src):
        roles_src = os.path.join(lib_dir, "agents", ide, "roles")
    if not os.path.isdir(roles_src):
        roles_src = os.path.join(lib_dir, "agents", "claude", "roles")
    if not os.path.isdir(roles_src):
        return 0
    roles_dst = os.path.join(target_dir, "roles")
    copy_dir(roles_src, roles_dst)
    return len([f for f in os.listdir(roles_dst) if f.endswith(".md")])


from bootstrap_stacks import copy_stacks  # noqa: F401, E402


def copy_references(lib_dir: str, target_dir: str, ide: str) -> int:
    """Copy shared + IDE-specific references."""
    refs_dst = os.path.join(target_dir, "references")
    os.makedirs(refs_dst, exist_ok=True)
    count = 0
    # Shared references
    shared_src = os.path.join(lib_dir, "references")
    if os.path.isdir(shared_src):
        for item in os.listdir(shared_src):
            src = os.path.join(shared_src, item)
            dst = os.path.join(refs_dst, item)
            if os.path.isdir(src):
                copy_dir(src, dst)
            else:
                shutil.copy2(src, dst)
            count += 1
    # IDE-specific references
    ide_refs = os.path.join(lib_dir, "agents", ide, "references")
    if os.path.isdir(ide_refs):
        for item in os.listdir(ide_refs):
            src = os.path.join(ide_refs, item)
            dst = os.path.join(refs_dst, item)
            if os.path.isdir(src):
                copy_dir(src, dst)
            else:
                shutil.copy2(src, dst)
            count += 1
    return count
