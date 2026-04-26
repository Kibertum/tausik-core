"""TAUSIK skill manager -- repo management, skill install/uninstall.

Handles TAUSIK-native skill repositories (tausik-skills.json format).
Incompatible repos get a clear error with link to adaptation guide.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any

TAUSIK_MANIFEST = "tausik-skills.json"
MANIFEST_FORMAT = "tausik-skills"
ADAPTATION_GUIDE = "docs/{lang}/skill-adaptation.md"


class SkillManagerError(Exception):
    """Raised on skill manager operations."""


# ---------------------------------------------------------------------------
# Repo format detection
# ---------------------------------------------------------------------------


def detect_repo_format(repo_dir: str) -> dict[str, Any]:
    """Detect skill repo format. Returns {format, manifest?, skills_count?}.

    Supported:
      - tausik-native: has tausik-skills.json in root
      - incompatible: anything else
    """
    manifest_path = os.path.join(repo_dir, TAUSIK_MANIFEST)
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            if manifest.get("format") == MANIFEST_FORMAT:
                skills = manifest.get("skills", {})
                return {
                    "format": "tausik-native",
                    "manifest": manifest,
                    "skills_count": len(skills),
                    "skill_names": sorted(skills.keys()),
                }
        except (json.JSONDecodeError, OSError):
            pass
    return {"format": "incompatible"}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_ALLOWED_URL_SCHEMES = ("https://", "http://", "git@", "ssh://")


def _validate_url(url: str) -> None:
    """Validate git URL scheme. Rejects dangerous protocols like ext::."""
    if not any(url.startswith(s) for s in _ALLOWED_URL_SCHEMES):
        raise SkillManagerError(
            f"Unsupported URL scheme: {url}\nAllowed: {', '.join(_ALLOWED_URL_SCHEMES)}"
        )


def _validate_path_inside(child: str, parent: str) -> None:
    """Ensure resolved child path is inside parent. Prevents path traversal."""
    real_child = os.path.realpath(child)
    real_parent = os.path.realpath(parent)
    if not real_child.startswith(real_parent + os.sep) and real_child != real_parent:
        raise SkillManagerError(f"Path traversal detected: {child} escapes {parent}")


# ---------------------------------------------------------------------------
# Repo cloning
# ---------------------------------------------------------------------------


def _repo_name_from_url(url: str) -> str:
    """Extract repo name from git URL."""
    name = url.rstrip("/").rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name


def clone_repo(url: str, vendor_dir: str) -> tuple[str, str]:
    """Shallow-clone a repo into vendor_dir. Returns (repo_dir, repo_name).

    If repo already exists, does git pull instead.
    """
    _validate_url(url)
    repo_name = _repo_name_from_url(url)
    repo_dir = os.path.join(vendor_dir, repo_name)

    if os.path.isdir(os.path.join(repo_dir, ".git")):
        # Already cloned -- pull latest
        try:
            result = subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            if result.returncode != 0:
                print(
                    f"  Warning: git pull failed for {repo_name}, using existing checkout"
                )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            print(f"  Warning: could not update {repo_name}, using existing checkout")
        return repo_dir, repo_name

    os.makedirs(vendor_dir, exist_ok=True)
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, repo_dir],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if result.returncode != 0:
            raise SkillManagerError(f"git clone failed: {result.stderr.strip()}")
    except FileNotFoundError:
        raise SkillManagerError("git not found. Install git to use skill repos.")
    except subprocess.TimeoutExpired:
        raise SkillManagerError("git clone timed out (120s). Check URL and network.")
    return repo_dir, repo_name


# ---------------------------------------------------------------------------
# Manifest operations
# ---------------------------------------------------------------------------


def load_manifest(repo_dir: str) -> dict[str, Any]:
    """Load and validate tausik-skills.json from repo."""
    path = os.path.join(repo_dir, TAUSIK_MANIFEST)
    if not os.path.isfile(path):
        raise SkillManagerError(
            f"Not a TAUSIK-compatible repo: {TAUSIK_MANIFEST} not found.\n"
            f"See {ADAPTATION_GUIDE.format(lang='en')} for how to adapt a skill repo."
        )
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise SkillManagerError(f"Invalid {TAUSIK_MANIFEST}: {e}")

    if manifest.get("format") != MANIFEST_FORMAT:
        raise SkillManagerError(
            f"{TAUSIK_MANIFEST} has wrong format: {manifest.get('format')!r}. "
            f"Expected: {MANIFEST_FORMAT!r}"
        )
    result: dict[str, Any] = manifest
    return result


def get_skill_info(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    """Get skill metadata from manifest. Raises if not found."""
    skills: dict[str, Any] = manifest.get("skills", {})
    if name not in skills:
        available = ", ".join(sorted(skills.keys()))
        raise SkillManagerError(
            f"Skill '{name}' not found in repo. Available: {available}"
        )
    info: dict[str, Any] = skills[name]
    return info


# ---------------------------------------------------------------------------
# Skill install / uninstall
# ---------------------------------------------------------------------------


def find_skill_source(
    vendor_dir: str, skill_name: str
) -> tuple[str, str, dict[str, Any]] | None:
    """Find a skill across all installed repos.

    Returns (repo_dir, repo_name, skill_info) or None.
    """
    if not os.path.isdir(vendor_dir):
        return None
    for repo_name in sorted(os.listdir(vendor_dir)):
        repo_dir = os.path.join(vendor_dir, repo_name)
        manifest_path = os.path.join(repo_dir, TAUSIK_MANIFEST)
        if not os.path.isfile(manifest_path):
            continue
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            skills = manifest.get("skills", {})
            if skill_name in skills:
                return repo_dir, repo_name, skills[skill_name]
        except (json.JSONDecodeError, OSError):
            continue
    return None


def copy_skill(
    repo_dir: str,
    skill_info: dict[str, Any],
    skill_name: str,
    skills_dst: str,
) -> str:
    """Copy skill from repo to IDE skills directory.

    Copies: SKILL.md, references/, scripts/, data/, templates/
    Skips: .claude-plugin/, hooks/, CLAUDE.md, .git*, __pycache__
    """
    skill_path = skill_info.get("path", f"{skill_name}/")
    source = os.path.join(repo_dir, skill_path.rstrip("/"))
    _validate_path_inside(source, repo_dir)
    if not os.path.isdir(source):
        raise SkillManagerError(
            f"Skill path '{skill_path}' not found in repo at {repo_dir}"
        )
    skill_md = os.path.join(source, "SKILL.md")
    if not os.path.isfile(skill_md):
        raise SkillManagerError(f"SKILL.md not found in {source}")

    dst = os.path.join(skills_dst, skill_name)

    # Remove existing (stub or old version)
    if os.path.exists(dst):
        shutil.rmtree(dst)

    # Copy with filter
    _SKIP_DIRS = {".claude-plugin", "hooks", ".git", "__pycache__", ".mypy_cache"}
    _SKIP_FILES = {"CLAUDE.md", ".gitignore", ".gitmodules"}

    def _ignore(directory: str, contents: list[str]) -> list[str]:
        ignored = []
        for item in contents:
            if item in _SKIP_DIRS and os.path.isdir(os.path.join(directory, item)):
                ignored.append(item)
            elif item in _SKIP_FILES:
                ignored.append(item)
            elif item.startswith(".git"):
                ignored.append(item)
        return ignored

    shutil.copytree(source, dst, ignore=_ignore)
    return dst


def install_skill_deps(
    repo_dir: str, skill_info: dict[str, Any], tausik_dir: str
) -> bool:
    """Install skill pip dependencies into .tausik/venv/.

    Dependencies come from skill_info["requires"] list.
    """
    import re as _re

    requires = skill_info.get("requires", [])
    if not requires:
        return True

    _SAFE_PKG = _re.compile(
        r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9._,-]+\])?"
        r"(?:[<>=!~]=?[\w.+*-]+)?$"
    )
    bad = [r for r in requires if not isinstance(r, str) or not _SAFE_PKG.match(r)]
    if bad:
        print(f"  REFUSED: unsafe package specs in 'requires': {bad}")
        return False

    print(f"  Installing dependencies: {', '.join(requires)}")
    print(
        "  WARNING: packages come from an external skill manifest. "
        "Review before use in production."
    )

    # Find venv python
    _bootstrap_dir = os.path.join(os.path.dirname(__file__), "..", "bootstrap")
    if _bootstrap_dir not in sys.path:
        sys.path.insert(0, _bootstrap_dir)
    try:
        from bootstrap_venv import get_venv_python  # type: ignore[import-not-found]
    except ImportError:
        return False

    venv_python = get_venv_python(tausik_dir)
    if not venv_python:
        print(f"  Warning: venv not found, cannot install deps: {requires}")
        return False

    try:
        result = subprocess.run(
            [venv_python, "-m", "pip", "install", "--quiet", "--"] + requires,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  pip install failed: {result.stderr}")
            return False
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"  pip install error: {e}")
        return False


def install_skill(
    skill_name: str,
    vendor_dir: str,
    skills_dst: str,
    config_path: str,
    tausik_dir: str,
) -> str:
    """Install a skill: find in repos, copy to IDE, install deps, update config.

    Returns status message.
    """
    found = find_skill_source(vendor_dir, skill_name)
    if not found:
        raise SkillManagerError(
            f"Skill '{skill_name}' not found in any repo. "
            f"Run 'tausik skill repo list' to see available skills."
        )
    repo_dir, repo_name, skill_info = found

    # Copy skill files
    copy_skill(repo_dir, skill_info, skill_name, skills_dst)

    # Install pip deps
    requires = skill_info.get("requires", [])
    if requires:
        ok = install_skill_deps(repo_dir, skill_info, tausik_dir)
        if not ok:
            return (
                f"Skill '{skill_name}' installed from {repo_name} "
                f"but dependency installation failed: {requires}"
            )

    # Update config
    from skill_repos import update_config_install

    update_config_install(config_path, skill_name, repo_name)

    deps_msg = f" Dependencies: {', '.join(requires)}" if requires else ""
    return f"Skill '{skill_name}' installed from {repo_name}.{deps_msg}"


def uninstall_skill(
    skill_name: str,
    skills_dst: str,
    config_path: str,
) -> str:
    """Uninstall a skill: remove from IDE skills dir and config."""
    dst = os.path.join(skills_dst, skill_name)
    if os.path.exists(dst):
        shutil.rmtree(dst)

    from skill_repos import update_config_uninstall

    update_config_uninstall(config_path, skill_name)
    return f"Skill '{skill_name}' uninstalled."
