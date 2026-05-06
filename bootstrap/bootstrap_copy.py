"""TAUSIK bootstrap file copy — skills, scripts, MCP servers with IDE awareness."""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any

# Skill-specific helpers live in bootstrap_skill_helpers (extracted in
# v14b polish Phase B to keep this module under the 400-line filesize
# gate). Re-exported here so external imports keep working:
#   - bootstrap.py: copy_skills (uses parse_skill_frontmatter internally)
#   - scripts/skill_profile.py: parse_skill_frontmatter
#   - tests/test_bootstrap_frontmatter.py: parse_skill_frontmatter, validate_skill_frontmatter
from bootstrap_skill_helpers import (  # noqa: F401
    VALID_CONTEXT,
    VALID_EFFORT,
    _generate_stub,
    _load_registry,
    _resolve_skill,
    parse_skill_frontmatter,
    validate_skill_frontmatter,
)


def _on_rmtree_error(func, path, exc_info):
    import logging
    import stat as _stat

    try:
        os.chmod(path, _stat.S_IWRITE)
        func(path)
    except Exception as e:
        logging.getLogger("tausik.bootstrap").warning(
            "rmtree retry failed for %s: %s (orig %s)", path, e, exc_info
        )
        raise


def _on_rmtree_exc(func, path, exc):
    _on_rmtree_error(func, path, (type(exc), exc, exc.__traceback__))


def _files_identical(a: str, b: str) -> bool:
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


def _conditional_copy(src: str, dst: str) -> None:
    if os.path.isfile(dst) and _files_identical(src, dst):
        return
    shutil.copy2(src, dst)


def copy_dir(src: str, dst: str) -> None:
    """Copy src→dst, skipping byte-identical files. Removes orphans.

    v1.3.4 (med-batch-1-hooks #3): symlinks=False — never preserve symlinks,
    always materialize the target file content. Skill or stack repos shipping
    a symlink that resolves to /etc/passwd or ~/.aws/credentials would
    otherwise leak the target into .claude/ on bootstrap.
    """
    _IGNORED = ("__pycache__", ".git")
    if not os.path.exists(dst):
        shutil.copytree(
            src,
            dst,
            ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc"),
            symlinks=False,
        )
        return
    expected: set[str] = set()
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in _IGNORED]
        for fname in files:
            if fname.endswith(".pyc"):
                continue
            rel = os.path.relpath(os.path.join(root, fname), src)
            expected.add(rel)
            target = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            _conditional_copy(os.path.join(root, fname), target)
    for root, dirs, files in os.walk(dst, topdown=False):
        for fname in files:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, dst)
            if rel not in expected:
                try:
                    os.unlink(full)
                except OSError:
                    pass
        for d in dirs:
            full = os.path.join(root, d)
            try:
                if not os.listdir(full):
                    os.rmdir(full)
            except OSError:
                pass


def copy_skills(
    lib_dir: str,
    target_dir: str,
    config: dict[str, Any],
    ide: str,
    vendor_skills: dict[str, str] | None = None,
    *,
    include_official_stubs: bool = False,
    brain_enabled: bool = True,
) -> int:
    """Copy skills to target IDE directory.

    Built-in skills (in harness/skills/) are always copied in full, except
    `brain` which is gated on `brain_enabled` (set by bootstrap from the
    project's brain config — `tausik brain init` flips it on).

    Official skills (skills-official/registry.json) are auto-stubbed only
    when `include_official_stubs=True` (CLI flag --include-official). Default
    is False since v1.4 to keep the system-reminder list small (~−1k tok/turn).
    Skills explicitly listed in config["installed_skills"] are still deployed
    (full copy) regardless of the flag — that's the per-skill opt-in.

    Vendor skills follow the same `installed_skills` rule.

    Resolution chain: harness/skills/ → adjacent dir → vendor downloads.
    """
    builtin_dir = os.path.join(lib_dir, "harness", "skills")
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

    # Built-in skills under harness/skills/ are source-of-truth.
    builtin_names: list[str] = []
    if os.path.isdir(builtin_dir):
        for name in sorted(os.listdir(builtin_dir)):
            if name.startswith(".") or name.startswith("_"):
                continue
            if name == "brain" and not brain_enabled:
                # v14b-skill-core-cleanup: brain stays in source but is not
                # surfaced into the system-reminder list until the project
                # has Notion configured (`tausik brain init`). Saves ~600
                # tokens/turn for projects that never use the shared brain.
                continue
            if os.path.isdir(os.path.join(builtin_dir, name)):
                builtin_names.append(name)
    if not builtin_names:
        print(
            f"  WARN: harness/skills/ empty or missing at {builtin_dir} — "
            "core skills will not be deployed (config-only fallback active).",
            file=sys.stderr,
        )
    config_skills = config.get("core_skills", []) + config.get("extension_skills", [])
    # v14b-skill-core-cleanup: drop registry-name entries that the user
    # didn't explicitly opt into. Without this filter, an `extension_skills`
    # auto-detected from the project (e.g. `docs`, `diff`) used to add a
    # stub even when --include-official was off, defeating the budget cut.
    registry_names = set(registry or {})
    if not include_official_stubs:
        explicit = installed | set(vendor_activated)
        config_skills = [s for s in config_skills if s in explicit or s not in registry_names]
    all_skills_with_vendor = list(dict.fromkeys(builtin_names + config_skills + vendor_activated))
    # Also add official skills from registry (as stubs) — v1.4 opt-in only.
    # Without --include-official the agent gets a smaller skill list and
    # discovers extras via `tausik skill list` / bundle CLI on demand.
    if registry and include_official_stubs:
        for name in registry:
            if name not in all_skills_with_vendor:
                all_skills_with_vendor.append(name)

    for skill in all_skills_with_vendor:
        src, source_type = _resolve_skill(skill, builtin_dir, adjacent_dir, vendor_skills)
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

    preserve = set(all_skills_with_vendor)
    if os.path.isdir(skills_dst):
        for existing in os.listdir(skills_dst):
            existing_path = os.path.join(skills_dst, existing)
            if os.path.isdir(existing_path) and existing not in preserve:
                if sys.version_info >= (3, 12):
                    shutil.rmtree(existing_path, onexc=_on_rmtree_exc)
                else:
                    shutil.rmtree(existing_path, onerror=_on_rmtree_error)

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
    """Copy MCP servers from harness/{ide}/mcp/ to target."""
    mcp_src = os.path.join(lib_dir, "harness", ide, "mcp")
    if not os.path.isdir(mcp_src):
        mcp_src = os.path.join(lib_dir, "harness", "claude", "mcp")
    if not os.path.isdir(mcp_src):
        return 0
    mcp_dst = os.path.join(target_dir, "mcp")
    copy_dir(mcp_src, mcp_dst)
    return len(os.listdir(mcp_dst))


def copy_roles(lib_dir: str, target_dir: str, ide: str) -> int:
    """Copy role profiles from harness/roles/ (shared) to target."""
    roles_src = os.path.join(lib_dir, "harness", "roles")
    if not os.path.isdir(roles_src):
        roles_src = os.path.join(lib_dir, "harness", ide, "roles")
    if not os.path.isdir(roles_src):
        roles_src = os.path.join(lib_dir, "harness", "claude", "roles")
    if not os.path.isdir(roles_src):
        return 0
    roles_dst = os.path.join(target_dir, "roles")
    copy_dir(roles_src, roles_dst)
    return len([f for f in os.listdir(roles_dst) if f.endswith(".md")])


from bootstrap_stacks import copy_stacks  # noqa: F401, E402


def copy_references(lib_dir: str, target_dir: str, ide: str) -> int:
    """v1.3+: references/ merged into docs/. Copy docs/ to target instead."""
    docs_dst = os.path.join(target_dir, "docs")
    docs_src = os.path.join(lib_dir, "docs")
    if not os.path.isdir(docs_src):
        return 0
    copy_dir(docs_src, docs_dst)
    count = sum(1 for _ in os.walk(docs_dst))
    ide_refs = os.path.join(lib_dir, "harness", ide, "references")
    if os.path.isdir(ide_refs):
        legacy_dst = os.path.join(target_dir, "references")
        os.makedirs(legacy_dst, exist_ok=True)
        for item in os.listdir(ide_refs):
            src = os.path.join(ide_refs, item)
            dst = os.path.join(legacy_dst, item)
            if os.path.isdir(src):
                copy_dir(src, dst)
            else:
                shutil.copy2(src, dst)
            count += 1
    return count
