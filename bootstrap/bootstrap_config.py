"""TAUSIK bootstrap configuration — config loading, stack detection, IDE selection."""

from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "core_skills": [
        "start",
        "end",
        "task",
        "plan",
        "checkpoint",
        "commit",
        "explore",
        "review",
        "test",
        "ship",
        "debug",
    ],
    "extension_skills": [],
    "installed_skills": [],
    "ide": "claude",
}

STACK_SIGNATURES: dict[str, list[tuple[str, str]]] = {
    "python": [("pyproject.toml", ""), ("requirements.txt", ""), ("setup.py", "")],
    "fastapi": [("requirements.txt", "fastapi"), ("pyproject.toml", "fastapi")],
    "django": [("manage.py", ""), ("requirements.txt", "django")],
    "react": [("package.json", '"react"')],
    "next": [("package.json", '"next"')],
    "vue": [("package.json", '"vue"')],
    "typescript": [("tsconfig.json", "")],
    "go": [("go.mod", "")],
    "rust": [("Cargo.toml", "")],
    "java": [("pom.xml", ""), ("build.gradle", "")],
    "laravel": [("artisan", ""), ("composer.json", "laravel")],
    "php": [("composer.json", "")],
}

# Extension skills are now in tausik/skills repo (official) or vendor repos.
# This list is used only by the analyzer for auto-detection hints.
ALL_EXTENSION_SKILLS = [
    "diff",
    "security",
    "docs",
    "optimize",
    "audit",
    "onboard",
    "retro",
    "pdf",
    "excel",
    "sentry",
    "ui-ux-pro-max",
    "ultra",
    "dispatch",
    "loop-task",
    "seo",
    "run",
    "daily",
    "init",
]


def load_config(config_path: str) -> dict[str, Any]:
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            import logging

            logging.getLogger("tausik.config").warning(
                "Config corrupted (%s): %s — using defaults", config_path, e
            )
    return dict(DEFAULT_CONFIG)


def save_config(config_path: str, cfg: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def detect_stacks(project_dir: str) -> list[str]:
    """Detect technology stacks by file signatures."""
    found: list[str] = []
    for stack, signatures in STACK_SIGNATURES.items():
        for filename, keyword in signatures:
            filepath = os.path.join(project_dir, filename)
            if os.path.exists(filepath):
                if not keyword:
                    found.append(stack)
                    break
                try:
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        content = f.read(65536)
                    if keyword in content:
                        found.append(stack)
                        break
                except OSError:
                    pass
    return list(set(found))


def detect_extension_skills(
    project_dir: str, core_skills: list[str] | None = None
) -> list[str]:
    """Smart-detect which extension skills are useful for this project.

    Skills that are already in core_skills are excluded to avoid duplicates.
    """
    _core = set(core_skills or [])
    skills: list[str] = []
    # Git
    if os.path.exists(os.path.join(project_dir, ".git")):
        skills.append("diff")
    # Security
    if os.path.exists(os.path.join(project_dir, ".env")):
        skills.append("security")
    # Docs
    for marker in ["docs/", "sphinx/", "mkdocs.yml", "docusaurus.config.js"]:
        if os.path.exists(os.path.join(project_dir, marker)):
            skills.append("docs")
            break
    return [s for s in set(skills) if s not in _core]
