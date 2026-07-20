"""TAUSIK SkillsMixin -- skill lifecycle: activate, deactivate, list, install."""

from __future__ import annotations

import os
from typing import Any

from tausik_utils import ServiceError


class SkillsMixin:
    """Skill lifecycle: activate, deactivate, list, install, uninstall."""

    @staticmethod
    def _validate_skill_name(name: str) -> None:
        import re

        if not name or ".." in name or "/" in name or "\\" in name:
            raise ServiceError(
                f"Invalid skill name '{name}': must not contain path separators or '..'"
            )
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
            raise ServiceError(
                f"Invalid skill name '{name}': must be lowercase alphanumeric with hyphens"
            )

    @staticmethod
    def _load_tausik_config(config_path: str) -> dict[str, Any]:
        """Load .tausik/config.json, return full dict."""
        import json
        import logging

        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    result: dict[str, Any] = json.load(f)
                    return result
            except (json.JSONDecodeError, OSError) as e:
                logging.getLogger("tausik.config").warning(
                    "Config corrupted (%s): %s -- using defaults", config_path, e
                )
        return {}

    @staticmethod
    def _save_tausik_config(config_path: str, cfg: dict[str, Any]) -> None:
        """Save .tausik/config.json."""
        import json

        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _is_stub_skill(skill_dir: str) -> bool:
        """Check if a skill directory contains only a stub (on-demand marker)."""
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            return False
        try:
            with open(skill_md, encoding="utf-8") as f:
                content = f.read(500)
            return "source: official" in content and "on-demand skill" in content
        except OSError:
            return False

    @staticmethod
    def _find_official_skill(project_dir: str, name: str) -> str | None:
        """Find skill in official skills directories.

        Search order:
        1. {project_dir}/skills-official/{name}  (same repo, split layout)
        2. {project_dir}/skills/{name}            (same repo, alt name)
        3. {parent}/skills-official/{name}         (adjacent repo: tausik/core + tausik/skills)
        4. {parent}/skills/{name}                  (adjacent repo, alt name)
        """
        for candidate in ("skills-official", "skills"):
            p = os.path.join(project_dir, candidate, name)
            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "SKILL.md")):
                return p
        parent = os.path.dirname(os.path.abspath(project_dir))
        for candidate in ("skills-official", "skills"):
            p = os.path.join(parent, candidate, name)
            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "SKILL.md")):
                return p
        return None

    @staticmethod
    def _find_vendor_skill(vendor_dir: str, name: str) -> tuple[str, str] | None:
        """Locate a vendor skill. Returns (skill_path, repo_name), or None.

        The repo name is not decoration: it is the lookup key for that repo's
        pinned publisher key, so activate can verify the signature the way
        install does.

        Sorted and collision-loud. Unsorted os.listdir let whichever repo the
        filesystem happened to yield first win, so a repo already added for one
        skill could silently shadow a popular name published by another.
        """
        if not os.path.isdir(vendor_dir):
            return None
        matches: list[tuple[str, str]] = []
        for vname in sorted(os.listdir(vendor_dir)):
            vpath = os.path.join(vendor_dir, vname)
            if not os.path.isdir(vpath):
                continue
            skill_path = os.path.join(vpath, name)
            if os.path.isdir(skill_path) and os.path.exists(os.path.join(skill_path, "SKILL.md")):
                matches.append((skill_path, vname))
        if not matches:
            return None
        if len(matches) > 1:
            repos = ", ".join(repo for _path, repo in matches)
            raise ServiceError(
                f"Skill '{name}' is published by more than one repo ({repos}). "
                f"Refusing to guess which one you meant — drop the repo you do "
                f"not trust: tausik skill repo remove <repo>"
            )
        return matches[0]

    @staticmethod
    def _verify_vendor_skill(
        name: str, source: str, repo_name: str, config_path: str | None
    ) -> str:
        """Publisher-signature check for a vendor skill. Returns a warning, or ''.

        activate used to skip this outright, so a skill that `skill install`
        blocked installed cleanly through `skill activate` — one verification,
        one path, everything else in through the side door. Mirrors install:
        block refuses, warn proceeds (same adoption path, no stricter, no looser).
        """
        from supply_verify_install import LEVEL_BLOCK, LEVEL_OK, check_skill_signature

        pinned: str | None = None
        if config_path:
            try:
                from skill_repos import get_repo_pinned_pubkey

                pinned = get_repo_pinned_pubkey(config_path, repo_name)
            except Exception as e:  # noqa: BLE001 — see fail-closed note below
                # A trust anchor we cannot read is not the same as one that says
                # "unpinned": the first is unknown, the second is a decision.
                raise ServiceError(
                    f"Cannot read the pinned publisher key for repo "
                    f"'{repo_name}' ({e}). Refusing to activate '{name}' on an "
                    f"unverifiable trust anchor."
                ) from e
        level, msg = check_skill_signature(source, repo_name, pinned)
        if level == LEVEL_BLOCK:
            raise ServiceError(f"Refusing to activate '{name}': {msg}")
        return "" if level == LEVEL_OK else f" WARNING: {msg}"

    @staticmethod
    def skill_activate(
        name: str,
        vendor_dir: str,
        skills_dst: str,
        lib_skills_dir: str,
        config_path: str | None = None,
    ) -> str:
        import shutil

        SkillsMixin._validate_skill_name(name)
        dst = os.path.join(skills_dst, name)

        # Check if already fully activated (not a stub)
        if os.path.exists(dst) and not SkillsMixin._is_stub_skill(dst):
            return f"Skill '{name}' already active."

        # Derive project_dir from skills_dst (e.g. .claude/skills -> project root)
        project_dir = os.path.dirname(os.path.dirname(skills_dst))
        # First-party skills ship inside the framework repo: nothing signs them
        # and nothing is expected to. Vendor skills come from a third party and
        # get the same signature check `skill install` applies.
        warning = ""
        source = SkillsMixin._find_official_skill(project_dir, name)
        if not source:
            found = SkillsMixin._find_vendor_skill(vendor_dir, name)
            if found:
                source, repo_name = found
                warning = SkillsMixin._verify_vendor_skill(name, source, repo_name, config_path)
        if not source:
            raise ServiceError(
                f"Skill '{name}' not found. Check skills repo or run bootstrap --update-deps."
            )

        # Replace stub (or create new) with full skill.
        # v1.3.4 (med-batch-1-hooks #3): symlinks=False to prevent vendor-repo
        # symlink-smuggling of absolute paths (~/.aws/credentials etc.) into
        # the activated skills tree.
        # skill_tree_ignore: the same strip-list install uses. Without it this
        # path copied hooks and plugin manifests straight into the tree.
        from skill_manager import skill_tree_ignore

        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(source, dst, ignore=skill_tree_ignore, symlinks=False)

        if config_path:
            cfg = SkillsMixin._load_tausik_config(config_path)
            bootstrap = cfg.setdefault("bootstrap", {})
            installed = bootstrap.setdefault("installed_skills", [])
            if name not in installed:
                installed.append(name)
            SkillsMixin._save_tausik_config(config_path, cfg)
        return f"Skill '{name}' activated (full version loaded).{warning}"

    @staticmethod
    def skill_deactivate(
        name: str, skills_dst: str, lib_skills_dir: str, config_path: str | None = None
    ) -> str:
        import shutil

        SkillsMixin._validate_skill_name(name)
        dst = os.path.join(skills_dst, name)
        if not os.path.exists(dst):
            raise ServiceError(f"Skill '{name}' is not active.")
        # Cannot deactivate built-in skills
        if os.path.isdir(os.path.join(lib_skills_dir, name)):
            raise ServiceError(f"Skill '{name}' is a built-in skill, cannot deactivate.")
        # If it's a stub already, nothing to deactivate
        if SkillsMixin._is_stub_skill(dst):
            return f"Skill '{name}' is already a stub (not loaded)."
        shutil.rmtree(dst)
        if config_path:
            cfg = SkillsMixin._load_tausik_config(config_path)
            bootstrap = cfg.get("bootstrap", {})
            for key in ("vendor_activated", "installed_skills"):
                lst = bootstrap.get(key, [])
                if name in lst:
                    lst.remove(name)
                    bootstrap[key] = lst
            SkillsMixin._save_tausik_config(config_path, cfg)
        return f"Skill '{name}' deactivated."

    @staticmethod
    def skill_list(vendor_dir: str, skills_dst: str) -> dict[str, list[dict[str, str]]]:
        active: list[dict[str, str]] = []
        vendored: list[dict[str, str]] = []
        active_names: set[str] = set()
        if os.path.isdir(skills_dst):
            active_names = {
                d for d in os.listdir(skills_dst) if os.path.isdir(os.path.join(skills_dst, d))
            }
        if os.path.isdir(vendor_dir):
            for vname in os.listdir(vendor_dir):
                vpath = os.path.join(vendor_dir, vname)
                if not os.path.isdir(vpath):
                    continue
                for item in os.listdir(vpath):
                    item_path = os.path.join(vpath, item)
                    if os.path.isdir(item_path) and os.path.exists(
                        os.path.join(item_path, "SKILL.md")
                    ):
                        entry = {"name": item, "vendor": vname}
                        if item in active_names:
                            active.append(entry)
                        else:
                            vendored.append(entry)
        return {"active": active, "vendored": vendored}

    @staticmethod
    def skill_install(
        name: str,
        vendor_dir: str,
        skills_dst: str,
        config_path: str,
        tausik_dir: str,
    ) -> str:
        """Install a skill from a TAUSIK-compatible repo."""
        from skill_manager import install_skill

        return install_skill(name, vendor_dir, skills_dst, config_path, tausik_dir)

    @staticmethod
    def skill_uninstall(name: str, skills_dst: str, config_path: str) -> str:
        """Uninstall a skill completely."""
        from skill_manager import uninstall_skill

        return uninstall_skill(name, skills_dst, config_path)

    @staticmethod
    def skill_catalog(
        vendor_dir: str,
        repo_name: str | None = None,
        config_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Discovery view: list skills offered by cloned skill repos.

        With ``repo_name=None`` returns rows from every repo whose
        ``tausik-skills.json`` manifest is readable. With an explicit
        ``repo_name`` returns only that repo's skills; raises
        ``ServiceError`` when the repo is neither configured nor cloned.
        """
        from skill_repos import load_config, repo_catalog

        if repo_name is not None:
            cfg_repos: dict[str, Any] = {}
            if config_path:
                cfg_repos = load_config(config_path).get("skill_repos", {})
            cloned = os.path.isdir(os.path.join(vendor_dir, repo_name))
            if not cloned and repo_name not in cfg_repos:
                raise ServiceError(
                    f"Skill repo '{repo_name}' is not configured and not cloned. "
                    "Use `tausik skill repo list` to see options."
                )
        return repo_catalog(vendor_dir, repo_name)
