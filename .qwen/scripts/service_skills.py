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
    def _find_vendor_skill(vendor_dir: str, name: str) -> str | None:
        if not os.path.isdir(vendor_dir):
            return None
        for vname in os.listdir(vendor_dir):
            vpath = os.path.join(vendor_dir, vname)
            if not os.path.isdir(vpath):
                continue
            skill_path = os.path.join(vpath, name)
            if os.path.isdir(skill_path) and os.path.exists(
                os.path.join(skill_path, "SKILL.md")
            ):
                return skill_path
        return None

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
        source = SkillsMixin._find_official_skill(project_dir, name)
        if not source:
            source = SkillsMixin._find_vendor_skill(vendor_dir, name)
        if not source:
            raise ServiceError(
                f"Skill '{name}' not found. Check skills repo or run bootstrap --update-deps."
            )

        # Replace stub (or create new) with full skill.
        # v1.3.4 (med-batch-1-hooks #3): symlinks=False to prevent vendor-repo
        # symlink-smuggling of absolute paths (~/.aws/credentials etc.) into
        # the activated skills tree.
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(source, dst, symlinks=False)

        if config_path:
            cfg = SkillsMixin._load_tausik_config(config_path)
            bootstrap = cfg.setdefault("bootstrap", {})
            installed = bootstrap.setdefault("installed_skills", [])
            if name not in installed:
                installed.append(name)
            SkillsMixin._save_tausik_config(config_path, cfg)
        return f"Skill '{name}' activated (full version loaded)."

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
            raise ServiceError(
                f"Skill '{name}' is a built-in skill, cannot deactivate."
            )
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
                d
                for d in os.listdir(skills_dst)
                if os.path.isdir(os.path.join(skills_dst, d))
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
