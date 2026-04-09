"""TAUSIK skill repos -- repo management, listing, config persistence.

Split from skill_manager.py to stay under 400 lines per file.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Any

from skill_manager import (
    ADAPTATION_GUIDE,
    TAUSIK_MANIFEST,
    SkillManagerError,
    clone_repo,
    detect_repo_format,
)

# Default TAUSIK skill repos (pre-configured)
DEFAULT_REPOS: dict[str, str] = {
    "tausik-skills": "https://github.com/Kibertum/tausik-skills",
}


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def load_config(config_path: str) -> dict[str, Any]:
    """Load .tausik/config.json."""
    if os.path.isfile(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                result: dict[str, Any] = json.load(f)
                return result
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config_path: str, cfg: dict[str, Any]) -> None:
    """Save .tausik/config.json."""
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def update_config_repo_add(config_path: str, name: str, url: str) -> None:
    """Add repo to config."""
    cfg = load_config(config_path)
    repos = cfg.setdefault("skill_repos", {})
    repos[name] = {"url": url}
    save_config(config_path, cfg)


def update_config_repo_remove(config_path: str, name: str) -> None:
    """Remove repo from config."""
    cfg = load_config(config_path)
    repos = cfg.get("skill_repos", {})
    repos.pop(name, None)
    save_config(config_path, cfg)


def update_config_install(config_path: str, skill_name: str, repo_name: str) -> None:
    """Mark skill as installed in config."""
    cfg = load_config(config_path)
    bootstrap = cfg.setdefault("bootstrap", {})
    installed = bootstrap.setdefault("installed_skills", [])
    if skill_name not in installed:
        installed.append(skill_name)
    save_config(config_path, cfg)


def update_config_uninstall(config_path: str, skill_name: str) -> None:
    """Remove skill from installed list in config."""
    cfg = load_config(config_path)
    bootstrap = cfg.get("bootstrap", {})
    for key in ("installed_skills", "vendor_activated"):
        lst = bootstrap.get(key, [])
        if skill_name in lst:
            lst.remove(skill_name)
    save_config(config_path, cfg)


# ---------------------------------------------------------------------------
# Repo management
# ---------------------------------------------------------------------------


def repo_add(url: str, vendor_dir: str, config_path: str) -> str:
    """Add a skill repo: clone + detect format + save to config."""
    repo_dir, repo_name = clone_repo(url, vendor_dir)
    info = detect_repo_format(repo_dir)

    if info["format"] != "tausik-native":
        # Clean up cloned repo
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise SkillManagerError(
            f"Repository '{repo_name}' is not TAUSIK-compatible "
            f"({TAUSIK_MANIFEST} not found or wrong format).\n\n"
            f"To make a skill repo compatible with TAUSIK, see:\n"
            f"  {ADAPTATION_GUIDE.format(lang='en')}\n\n"
            f"You can fork the repo, add {TAUSIK_MANIFEST}, and try again."
        )

    # Save to config
    update_config_repo_add(config_path, repo_name, url)

    names = ", ".join(info["skill_names"][:10])
    suffix = (
        f" (+{info['skills_count'] - 10} more)" if info["skills_count"] > 10 else ""
    )
    return (
        f"Repository '{repo_name}' added ({info['skills_count']} skills).\n"
        f"Available: {names}{suffix}\n"
        f"Install with: tausik skill install <name>"
    )


def repo_remove(name: str, vendor_dir: str, config_path: str) -> str:
    """Remove a skill repo from vendor dir and config."""
    repo_dir = os.path.join(vendor_dir, name)
    if os.path.isdir(repo_dir):
        shutil.rmtree(repo_dir)
    update_config_repo_remove(config_path, name)
    return f"Repository '{name}' removed."


def repo_list(vendor_dir: str, config_path: str) -> list[dict[str, Any]]:
    """List all configured skill repos with their skills."""
    cfg = load_config(config_path)
    repos = cfg.get("skill_repos", {})

    result = []
    for name, info in sorted(repos.items()):
        url = info if isinstance(info, str) else info.get("url", "")
        repo_dir = os.path.join(vendor_dir, name)
        skills: list[str] = []
        if os.path.isdir(repo_dir):
            manifest_path = os.path.join(repo_dir, TAUSIK_MANIFEST)
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        m = json.load(f)
                    skills = sorted(m.get("skills", {}).keys())
                except (json.JSONDecodeError, OSError):
                    pass
        result.append(
            {
                "name": name,
                "url": url,
                "skills": skills,
                "cloned": os.path.isdir(repo_dir),
            }
        )

    # Include default repos not yet added
    for name, url in DEFAULT_REPOS.items():
        if name not in repos:
            result.append(
                {
                    "name": name,
                    "url": url,
                    "skills": [],
                    "cloned": False,
                    "default": True,
                }
            )

    return result


def repo_list_all_skills(vendor_dir: str) -> list[dict[str, Any]]:
    """List all skills across all repos."""
    result: list[dict[str, Any]] = []
    if not os.path.isdir(vendor_dir):
        return result
    for repo_name in sorted(os.listdir(vendor_dir)):
        repo_dir = os.path.join(vendor_dir, repo_name)
        manifest_path = os.path.join(repo_dir, TAUSIK_MANIFEST)
        if not os.path.isfile(manifest_path):
            continue
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            for skill_name, info in sorted(manifest.get("skills", {}).items()):
                result.append(
                    {
                        "name": skill_name,
                        "repo": repo_name,
                        "description": info.get("description", ""),
                        "triggers": info.get("triggers", []),
                        "requires": info.get("requires", []),
                    }
                )
        except (json.JSONDecodeError, OSError):
            continue
    return result
