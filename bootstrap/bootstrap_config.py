"""TAUSIK bootstrap configuration — config loading, stack detection, IDE selection."""

from __future__ import annotations

import datetime
import json
import os
import sys
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

# Hardcoded fallback signatures — used when stack_registry can't be loaded
# (very early bootstrap, missing stacks/ dir). The canonical source is
# `<repo>/stacks/<name>/stack.json` consumed via `stack_registry`.
_FALLBACK_STACK_SIGNATURES: dict[str, list[tuple[str, str]]] = {
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
    "terraform": [("*.tf", ""), ("*.tfvars", "")],
    "ansible": [("ansible.cfg", ""), ("playbooks/", ""), ("roles/", "")],
    "helm": [("Chart.yaml", ""), ("Chart.yml", "")],
    "kubernetes": [("k8s/", ""), ("manifests/", ""), (".kube/", "")],
    "docker": [("Dockerfile", ""), ("Containerfile", "")],
}


def _load_stack_signatures() -> dict[str, list[tuple[str, str]]]:
    """Build STACK_SIGNATURES from stack_registry, falling back to hardcoded.

    Each registry decl entry `{file, type, keyword}` is rendered to the
    `(filename, keyword)` tuple form _signature_match() understands:
      * type=exact   → use file as-is
      * type=glob    → keep as-is (containing '*')
      * type=dir-marker → append a trailing '/' so _signature_match treats it as dir
    """
    try:
        import os as _os
        import sys as _sys

        # bootstrap/ → repo root → scripts/ for the registry import.
        _scripts = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "scripts"
        )
        if _scripts not in _sys.path:
            _sys.path.insert(0, _scripts)
        from stack_registry import default_registry

        reg = default_registry()
        out: dict[str, list[tuple[str, str]]] = {}
        for name in reg.all_stacks():
            entries: list[tuple[str, str]] = []
            for sig in reg.signatures_for(name):
                f = sig.get("file", "")
                t = sig.get("type", "exact")
                k = sig.get("keyword", "") or ""
                if t == "dir-marker" and not f.endswith("/"):
                    f = f + "/"
                entries.append((f, k))
            if entries:
                out[name] = entries
        if out:
            return out
        return _FALLBACK_STACK_SIGNATURES
    except Exception:  # noqa: BLE001 — bootstrap must boot even on broken registry
        import logging

        logging.getLogger("tausik.bootstrap").warning(
            "Stack registry unavailable; using hardcoded STACK_SIGNATURES",
            exc_info=True,
        )
        return _FALLBACK_STACK_SIGNATURES


STACK_SIGNATURES: dict[str, list[tuple[str, str]]] = _load_stack_signatures()

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


def _signature_match(project_dir: str, filename: str) -> str | None:
    """Resolve a signature pattern to a concrete path, or None if no match.

    Supports three forms:
      - exact filename → os.path.isfile
      - glob pattern (contains '*') → recursive glob with small depth cap
      - path ending with '/' → os.path.isdir
    """
    if filename.endswith("/"):
        return (
            os.path.join(project_dir, filename.rstrip("/"))
            if os.path.isdir(os.path.join(project_dir, filename.rstrip("/")))
            else None
        )
    if "*" in filename:
        import glob

        # Search up to 3 levels deep — covers monorepos like modules/aws/main.tf
        for depth in ("", "*/", "*/*/"):
            for hit in glob.glob(os.path.join(project_dir, depth + filename)):
                if os.path.isfile(hit):
                    return hit
        return None
    candidate = os.path.join(project_dir, filename)
    return candidate if os.path.isfile(candidate) else None


def detect_stacks(project_dir: str) -> list[str]:
    """Detect technology stacks by file signatures."""
    found: list[str] = []
    for stack, signatures in STACK_SIGNATURES.items():
        for filename, keyword in signatures:
            match = _signature_match(project_dir, filename)
            if match is None:
                continue
            if not keyword:
                found.append(stack)
                break
            # Keyword check only meaningful for files (not directories).
            if not os.path.isfile(match):
                continue
            try:
                with open(match, encoding="utf-8", errors="ignore") as f:
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


def save_tausik_config(
    tausik_config_path: str,
    config: dict,
    lib_commit: str | None,
    stacks: list[str],
    ides: list[str],
    project_dir: str,
    get_ide_target_fn: Any = None,
    lib_dir: str | None = None,
) -> None:
    """Save unified config, auto-enable gates, clean up old files.

    lib_dir: path to TAUSIK library root (for scripts/ import).
    """
    tausik_config: dict = {}
    if os.path.exists(tausik_config_path):
        try:
            with open(tausik_config_path, encoding="utf-8") as f:
                tausik_config = json.load(f)
        except (json.JSONDecodeError, OSError):
            tausik_config = {}
    config["_meta"] = {
        "lib_commit": lib_commit or "unknown",
        "generated_at": datetime.datetime.now().isoformat(),
        "skills_included": config.get("core_skills", [])
        + config.get("extension_skills", []),
    }
    tausik_config["bootstrap"] = config
    tausik_config.setdefault("rag", {})["mode"] = "fts5"
    if stacks:
        _lib = lib_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        scripts_path = os.path.join(_lib, "scripts")
        if scripts_path not in sys.path:
            sys.path.insert(0, scripts_path)
        try:
            from project_config import auto_enable_gates_for_stacks

            newly = auto_enable_gates_for_stacks(tausik_config, stacks)
            if newly:
                print(
                    f"  Gates auto-enabled for {', '.join(stacks)}: {', '.join(newly)}"
                )
        except ImportError:
            pass
    os.makedirs(os.path.dirname(tausik_config_path), exist_ok=True)
    with open(tausik_config_path, "w", encoding="utf-8") as f:
        json.dump(tausik_config, f, indent=2, ensure_ascii=False)
    if get_ide_target_fn:
        for ide in ides:
            old = os.path.join(
                get_ide_target_fn(project_dir, ide), ".tausik-bootstrap.json"
            )
            if os.path.exists(old):
                os.remove(old)
                print(f"  Migrated: removed old {old}")
