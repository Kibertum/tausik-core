"""TAUSIK vendor — download and manage external skill dependencies.

Downloads GitHub repos as tarballs, extracts skill directories,
and maintains .lock files for version tracking. Zero external deps.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import posixpath
import shutil
import tarfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


def load_skills_json(lib_dir: str) -> dict[str, Any]:
    """Load skills.json manifest from library root."""
    path = os.path.join(lib_dir, "skills.json")
    if not os.path.exists(path):
        return {"external_skills": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_lock(vendor_dir: str, name: str) -> dict[str, str] | None:
    """Read .lock file for a vendored skill."""
    lock_path = os.path.join(vendor_dir, name, ".lock")
    if not os.path.exists(lock_path):
        return None
    with open(lock_path, encoding="utf-8") as f:
        return json.load(f)


def _write_lock(vendor_dir: str, name: str, ref: str, sha: str) -> None:
    """Write .lock file after successful sync."""
    lock_dir = os.path.join(vendor_dir, name)
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, ".lock")
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "ref": ref,
                "sha": sha,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
            indent=2,
        )


def _download_tarball(repo: str, ref: str) -> bytes:
    """Download GitHub tarball for repo@ref. Returns raw bytes."""
    url = f"https://github.com/{repo}/archive/refs/tags/{ref}.tar.gz"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "tausik-bootstrap/1.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError:
        # Fallback: try as branch/commit ref
        url = f"https://github.com/{repo}/archive/{ref}.tar.gz"
        req = urllib.request.Request(
            url, headers={"User-Agent": "tausik-bootstrap/1.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()


def _resolve_symlink(symlink_path: str, link_target: str) -> str:
    """Resolve a symlink target relative to the symlink's directory (within tarball paths)."""
    parent = posixpath.dirname(symlink_path)
    return posixpath.normpath(posixpath.join(parent, link_target))


def _extract_skill_dirs(
    tarball_bytes: bytes,
    vendor_skill_dir: str,
    skill_dirs: list[str],
    scripts_dir: str | None = None,
    agents_dir: str | None = None,
    data_dirs: dict[str, str] | None = None,
) -> dict[str, int]:
    """Extract specific directories from tarball into vendor dir.

    Args:
        data_dirs: Mapping of {source_path: dest_subdir} for additional data to
                   extract into each skill directory. E.g. {"src/data": "data"}
                   will extract src/data/* into <skill>/data/*.

    Returns counts of extracted items per category.
    """
    counts: dict[str, int] = {"skills": 0, "scripts": 0, "agents": 0, "data": 0}

    # Clean target dir (except .lock)
    if os.path.exists(vendor_skill_dir):
        for item in os.listdir(vendor_skill_dir):
            if item == ".lock":
                continue
            path = os.path.join(vendor_skill_dir, item)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    os.makedirs(vendor_skill_dir, exist_ok=True)

    with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz") as tar:
        members = tar.getmembers()
        if not members:
            return counts
        root_prefix = members[0].name.split("/")[0] + "/"

        # Build symlink map for resolution: rel_path -> resolved_target
        symlink_map: dict[str, str] = {}
        for member in members:
            if member.issym() and member.name.startswith(root_prefix):
                rel = member.name[len(root_prefix) :]
                if rel:
                    resolved = _resolve_symlink(rel, member.linkname)
                    # Security: reject symlinks that escape the repo root
                    if resolved.startswith("..") or resolved.startswith("/"):
                        continue
                    symlink_map[rel] = resolved

        for member in members:
            if not member.name.startswith(root_prefix):
                continue
            rel_path = member.name[len(root_prefix) :]
            if not rel_path:
                continue

            # Check if this file belongs to a skill dir
            for skill_dir in skill_dirs:
                prefix = skill_dir.rstrip("/") + "/"
                if rel_path == skill_dir.rstrip("/") or rel_path.startswith(prefix):
                    skill_name = os.path.basename(skill_dir.rstrip("/"))
                    dest_rel = (
                        skill_name + "/" + rel_path[len(prefix) :]
                        if rel_path.startswith(prefix)
                        else skill_name + "/"
                    )
                    _extract_member(tar, member, vendor_skill_dir, dest_rel)
                    if member.isfile():
                        counts["skills"] += 1
                    break

            # Symlink resolution: if a symlink in a skill_dir points to another
            # location in the repo, extract files from that target location
            for sym_path, sym_target in symlink_map.items():
                for skill_dir in skill_dirs:
                    prefix = skill_dir.rstrip("/") + "/"
                    if not sym_path.startswith(prefix):
                        continue
                    # sym_path is inside a skill_dir; check if rel_path is under sym_target
                    target_prefix = sym_target.rstrip("/") + "/"
                    if rel_path.startswith(target_prefix) and member.isfile():
                        # Map: target file -> skill/symlink_subdir/file
                        sym_subdir = sym_path[len(prefix) :]
                        file_rel = rel_path[len(target_prefix) :]
                        skill_name = os.path.basename(skill_dir.rstrip("/"))
                        dest_rel = f"{skill_name}/{sym_subdir}/{file_rel}"
                        _extract_member(tar, member, vendor_skill_dir, dest_rel)
                        counts["data"] += 1

            # Data dirs: extract additional directories into skill subdirs
            if data_dirs:
                for data_src, data_dest in data_dirs.items():
                    data_prefix = data_src.rstrip("/") + "/"
                    if rel_path.startswith(data_prefix) or rel_path == data_src.rstrip(
                        "/"
                    ):
                        # Determine target skill (first skill in list, or use data_dest as-is)
                        skill_name = (
                            os.path.basename(skill_dirs[0].rstrip("/"))
                            if skill_dirs
                            else "data"
                        )
                        if rel_path == data_src.rstrip("/"):
                            dest_rel = f"{skill_name}/{data_dest}/"
                        else:
                            file_rel = rel_path[len(data_prefix) :]
                            dest_rel = f"{skill_name}/{data_dest}/{file_rel}"
                        _extract_member(tar, member, vendor_skill_dir, dest_rel)
                        if member.isfile():
                            counts["data"] += 1

            # Scripts
            if scripts_dir and rel_path.startswith(scripts_dir.rstrip("/") + "/"):
                dest_rel = "scripts/" + rel_path[len(scripts_dir.rstrip("/") + "/") :]
                _extract_member(tar, member, vendor_skill_dir, dest_rel)
                if member.isfile():
                    counts["scripts"] += 1

            # Agents
            if agents_dir and rel_path.startswith(agents_dir.rstrip("/") + "/"):
                dest_rel = "agents/" + rel_path[len(agents_dir.rstrip("/") + "/") :]
                _extract_member(tar, member, vendor_skill_dir, dest_rel)
                if member.isfile():
                    counts["agents"] += 1

    return counts


def _extract_member(
    tar: tarfile.TarFile, member: tarfile.TarInfo, base_dir: str, dest_rel: str
) -> None:
    """Safely extract a single tarfile member to base_dir/dest_rel."""
    # Allow regular files and directories — block hardlinks, devices
    # Symlinks are resolved in _extract_skill_dirs, not here
    if not (member.isfile() or member.isdir()):
        return
    dest_path = os.path.normpath(os.path.join(base_dir, dest_rel))
    # Path traversal protection
    if not dest_path.startswith(os.path.normpath(base_dir)):
        return
    if member.isdir():
        os.makedirs(dest_path, exist_ok=True)
    elif member.isfile():
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with tar.extractfile(member) as src:  # type: ignore[union-attr]
            if src:
                with open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)


def _read_plugin_json(
    tarball_bytes: bytes, max_size: int = 1_000_000
) -> dict[str, Any] | None:
    """Read .claude-plugin/plugin.json from tarball if it exists. Capped at max_size bytes."""
    with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz") as tar:
        members = tar.getmembers()
        if not members:
            return None
        root_prefix = members[0].name.split("/")[0] + "/"
        for member in members:
            rel = (
                member.name[len(root_prefix) :]
                if member.name.startswith(root_prefix)
                else ""
            )
            if rel == ".claude-plugin/plugin.json" and member.isfile():
                with tar.extractfile(member) as f:
                    if f:
                        data = f.read(max_size)
                        if len(data) >= max_size:
                            return None  # Too large, skip
                        try:
                            return json.loads(data)
                        except (json.JSONDecodeError, ValueError):
                            return None
    return None


def _write_plugin_meta(vendor_skill_dir: str, meta: dict[str, Any]) -> None:
    """Write plugin metadata to vendor dir for reference."""
    path = os.path.join(vendor_skill_dir, ".plugin.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def sync_deps(lib_dir: str, vendor_dir: str, force: bool = False) -> dict[str, Any]:
    """Sync all external skill dependencies. Returns status per skill."""
    manifest = load_skills_json(lib_dir)
    external = manifest.get("external_skills", {})
    results: dict[str, Any] = {}

    for name, spec in external.items():
        repo = spec["repo"]
        ref = spec.get("ref", "main")
        skill_dirs = spec.get("skill_dirs", [name])
        scripts_dir = spec.get("scripts_dir")
        agents_dir = spec.get("agents_dir")
        data_dirs = spec.get("data_dirs")  # {src_path: dest_subdir}

        lock = _read_lock(vendor_dir, name)
        if lock and lock.get("ref") == ref and not force:
            results[name] = {"status": "up-to-date", "ref": ref}
            continue

        print(f"  Downloading {repo}@{ref}...")
        try:
            tarball = _download_tarball(repo, ref)
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}
            continue

        vendor_skill_dir = os.path.join(vendor_dir, name)
        counts = _extract_skill_dirs(
            tarball, vendor_skill_dir, skill_dirs, scripts_dir, agents_dir, data_dirs
        )
        # Read plugin metadata if available
        plugin_meta = _read_plugin_json(tarball)
        if plugin_meta:
            _write_plugin_meta(vendor_skill_dir, plugin_meta)
        _write_lock(vendor_dir, name, ref, hashlib.sha256(tarball).hexdigest())
        results[name] = {"status": "synced", "ref": ref, **counts}
        data_count = counts.get("data", 0)
        print(
            f"  {name}: {counts['skills']} skill files, {data_count} data files, {counts['scripts']} scripts, {counts['agents']} agents"
        )

    return results


def get_vendor_skill_dirs(vendor_dir: str) -> dict[str, str]:
    """Get mapping of vendor skill name -> directory path for copy_skills integration."""
    skill_map: dict[str, str] = {}
    if not os.path.isdir(vendor_dir):
        return skill_map
    for name in os.listdir(vendor_dir):
        vendor_skill = os.path.join(vendor_dir, name)
        if not os.path.isdir(vendor_skill):
            continue
        # Each subdir inside the vendor skill is a skill directory
        for item in os.listdir(vendor_skill):
            item_path = os.path.join(vendor_skill, item)
            if os.path.isdir(item_path) and item not in (
                "scripts",
                "agents",
                "__pycache__",
            ):
                skill_md = os.path.join(item_path, "SKILL.md")
                if os.path.exists(skill_md):
                    skill_map[item] = item_path
    return skill_map


def get_vendor_scripts(vendor_dir: str) -> list[str]:
    """Get list of vendor script directories for copying."""
    dirs: list[str] = []
    if not os.path.isdir(vendor_dir):
        return dirs
    for name in os.listdir(vendor_dir):
        scripts_dir = os.path.join(vendor_dir, name, "scripts")
        if os.path.isdir(scripts_dir):
            dirs.append(scripts_dir)
    return dirs


def get_vendor_agents(vendor_dir: str) -> list[str]:
    """Get list of vendor agent directories for copying."""
    dirs: list[str] = []
    if not os.path.isdir(vendor_dir):
        return dirs
    for name in os.listdir(vendor_dir):
        agents_dir = os.path.join(vendor_dir, name, "agents")
        if os.path.isdir(agents_dir):
            dirs.append(agents_dir)
    return dirs


def copy_vendor_assets(vendor_dir: str, target_dir: str) -> None:
    """Copy vendor scripts and agents to namespaced subdirs.

    Prevents core file overwrites by namespacing: scripts/vendor_{name}/.
    """
    for scripts_src in get_vendor_scripts(vendor_dir):
        vendor_name = os.path.basename(os.path.dirname(scripts_src))
        scripts_dst = os.path.join(target_dir, "scripts", f"vendor_{vendor_name}")
        os.makedirs(scripts_dst, exist_ok=True)
        for f in os.listdir(scripts_src):
            src = os.path.join(scripts_src, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(scripts_dst, f))
    for agents_src in get_vendor_agents(vendor_dir):
        vendor_name = os.path.basename(os.path.dirname(agents_src))
        agents_dst = os.path.join(target_dir, "agents", f"vendor_{vendor_name}")
        os.makedirs(agents_dst, exist_ok=True)
        for f in os.listdir(agents_src):
            src = os.path.join(agents_src, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(agents_dst, f))
