"""TAUSIK skill manager -- repo management, skill install/uninstall.

Handles TAUSIK-native skill repositories (tausik-skills.json format).
Incompatible repos get a clear error with link to adaptation guide.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from typing import Any

TAUSIK_MANIFEST = "tausik-skills.json"
MANIFEST_FORMAT = "tausik-skills"
ADAPTATION_GUIDE = "docs/{lang}/skill-adaptation.md"

# Re-exported: git helpers and dependency installation live in sibling modules
# (filesize cap). Public names keep working for callers and tests.
from skill_git import (  # noqa: E402,F401
    EOL_PINS as _EOL_PINS,
    eol_is_pinned as _eol_is_pinned,
    pin_eol_config as _pin_eol_config,
    rmtree_force,
)

# Re-exported: dependency installation lives in skill_deps (filesize cap).
from skill_deps import (  # noqa: E402,F401
    DEFAULT_PIP_INDEX_URL,
    _resolve_venv_python,
    install_skill_deps,
)


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
        if not _eol_is_pinned(repo_dir):
            # Cloned by a build that inherited the user's core.autocrlf, so these
            # bytes may already differ from the repository's. A stale cache that
            # silently fails signature checks is worse than a re-clone.
            print(f"  Re-cloning {repo_name}: cached checkout predates EOL pinning.")
            rmtree_force(repo_dir)
        else:
            try:
                result = subprocess.run(
                    ["git", "pull", "--ff-only"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                    stdin=subprocess.DEVNULL,
                )
                if result.returncode != 0:
                    print(f"  Warning: git pull failed for {repo_name}, using existing checkout")
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                print(f"  Warning: could not update {repo_name}, using existing checkout")
            return repo_dir, repo_name

    os.makedirs(vendor_dir, exist_ok=True)
    try:
        result = subprocess.run(
            ["git", *_EOL_PINS, "clone", "--depth", "1", url, repo_dir],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise SkillManagerError(f"git clone failed: {result.stderr.strip()}")
    except FileNotFoundError:
        raise SkillManagerError("git not found. Install git to use skill repos.")
    except subprocess.TimeoutExpired:
        raise SkillManagerError("git clone timed out (120s). Check URL and network.")
    _pin_eol_config(repo_dir)
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
        raise SkillManagerError(f"Skill '{name}' not found in repo. Available: {available}")
    info: dict[str, Any] = skills[name]
    return info


# ---------------------------------------------------------------------------
# Skill install / uninstall
# ---------------------------------------------------------------------------


def find_skill_source(vendor_dir: str, skill_name: str) -> tuple[str, str, dict[str, Any]] | None:
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
        raise SkillManagerError(f"Skill path '{skill_path}' not found in repo at {repo_dir}")
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

    # v1.3.4 (med-batch-1-hooks #3): symlinks=False — never preserve symlinks,
    # so a hostile vendor repo cannot smuggle absolute paths (e.g.
    # ~/.aws/credentials, /etc/shadow) into the activated skills tree.
    shutil.copytree(source, dst, ignore=_ignore, symlinks=False)
    return dst


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

    # v15-supplychain-verify-install: check the publisher signature BEFORE
    # any file lands in the IDE skills tree. block = refuse; warn = proceed
    # (adoption path — unsigned repos / no pinned key yet).
    from skill_repos import get_repo_pinned_pubkey
    from supply_verify_install import LEVEL_BLOCK, check_skill_signature

    src = os.path.join(repo_dir, skill_info.get("path", f"{skill_name}/").rstrip("/"))
    sig_level, sig_msg = check_skill_signature(
        src, repo_name, get_repo_pinned_pubkey(config_path, repo_name)
    )
    if sig_level == LEVEL_BLOCK:
        raise SkillManagerError(sig_msg)

    # Copy skill files
    dst = copy_skill(repo_dir, skill_info, skill_name, skills_dst)

    # Install pip deps
    requires = skill_info.get("requires", [])
    if requires:
        ok = install_skill_deps(repo_dir, skill_info, tausik_dir)
        if not ok:
            # Fail closed. This used to print a message and return 0: the skill
            # sat in the skills tree unable to run, and every caller that reads an
            # exit code — CI, MCP, a shell script — saw success. A skill whose
            # declared dependencies are missing is not installed.
            #
            # The signature verdict survives the failure: it is what the user needs
            # in order to decide whether to install the packages by hand.
            try:
                rmtree_force(dst)
            except OSError:  # pragma: no cover - leave the mess, but report it
                pass
            verdict = (
                "Supply-chain: signature verified." if sig_level == "ok" else f"WARNING: {sig_msg}"
            )
            raise SkillManagerError(
                f"Skill '{skill_name}' from {repo_name} was NOT installed: "
                f"its dependencies failed to install ({', '.join(requires)}). "
                f"{verdict} "
                f"Install them yourself and retry:\n"
                f"  .tausik/venv/bin/python -m pip install {' '.join(requires)}\n"
                f"  tausik skill install {skill_name}"
            )

    # Update config
    from skill_repos import update_config_install

    update_config_install(config_path, skill_name, repo_name)

    deps_msg = f" Dependencies: {', '.join(requires)}" if requires else ""
    if sig_level == "ok":
        sig_note = " Supply-chain: signature verified."
    else:
        sig_note = f" WARNING: {sig_msg}"
    return f"Skill '{skill_name}' installed from {repo_name}.{deps_msg}{sig_note}"


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
