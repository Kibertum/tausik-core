#!/usr/bin/env python3
"""TAUSIK bootstrap — generate IDE-specific directory from library sources.

Usage:
    python .tausik-lib/bootstrap/bootstrap.py --ide claude --smart
    python .tausik-lib/bootstrap/bootstrap.py --ide cursor
    python .tausik-lib/bootstrap/bootstrap.py --ide all --smart
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

# Add bootstrap dir to path
_bootstrap_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _bootstrap_dir)

from bootstrap_config import (
    ALL_EXTENSION_SKILLS,
    DEFAULT_CONFIG,
    detect_extension_skills,
    detect_stacks,
    load_config,
    save_tausik_config,
)
from bootstrap_copy import (
    copy_mcp,
    copy_references,
    copy_roles,
    copy_scripts,
    copy_skills,
    copy_stacks,
)
from bootstrap_vendor import (
    copy_vendor_assets,
    get_vendor_skill_dirs,
    load_skills_json,
    sync_deps,
)
from bootstrap_venv import ensure_venv, install_requirements
from bootstrap_catalog import generate_skill_catalog
from bootstrap_generate import (
    generate_agents_md,
    generate_claude_md,
    generate_cursorrules,
    generate_mcp_json,
    generate_settings_claude,
)
from bootstrap_qwen import generate_qwen_md, generate_settings_qwen


def get_lib_commit(lib_dir: str) -> str | None:
    """Get current git commit of the library."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=lib_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


_IDE_DIRS = {
    "claude": ".claude",
    "cursor": ".cursor",
    "windsurf": ".windsurf",
    "codex": ".codex",
    "qwen": ".qwen",
}


def get_ide_target(project_dir: str, ide: str) -> str:
    """Get target directory for IDE."""
    subdir = _IDE_DIRS.get(ide)
    if not subdir:
        raise ValueError(f"Unknown IDE: {ide}. Supported: {sorted(_IDE_DIRS)}")
    return os.path.join(project_dir, subdir)


def bootstrap_ide(
    lib_dir: str,
    project_dir: str,
    ide: str,
    config: dict,
    stacks: list[str],
    vendor_skills: dict[str, str] | None = None,
    venv_python: str | None = None,
) -> None:
    """Bootstrap for a single IDE."""
    target_dir = get_ide_target(project_dir, ide)
    os.makedirs(target_dir, exist_ok=True)
    print(f"\n=== Bootstrapping for {ide} -> {target_dir} ===")

    # Copy files (with vendor fallback)
    n_skills = copy_skills(lib_dir, target_dir, config, ide, vendor_skills)
    print(f"  Skills: {n_skills} copied")

    n_scripts = copy_scripts(lib_dir, target_dir)
    print(f"  Scripts: {n_scripts} copied")

    n_mcp = copy_mcp(lib_dir, target_dir, ide)
    print(f"  MCP servers: {n_mcp} copied")

    n_refs = copy_references(lib_dir, target_dir, ide)
    print(f"  References: {n_refs} copied")

    n_roles = copy_roles(lib_dir, target_dir, ide)
    print(f"  Roles: {n_roles} copied")

    n_stacks = copy_stacks(lib_dir, target_dir, ide, stacks)
    print(f"  Stacks: {n_stacks} copied")

    # Stack customization hint — surfaced once on each bootstrap so users
    # know the safe path to override stack behaviour without losing it on
    # the next upgrade. Bootstrap NEVER touches .tausik/stacks/.
    user_stacks_dir = os.path.join(project_dir, ".tausik", "stacks")
    if os.path.isdir(user_stacks_dir):
        existing = [
            d
            for d in os.listdir(user_stacks_dir)
            if os.path.isdir(os.path.join(user_stacks_dir, d))
        ]
        if existing:
            print(
                f"  User stack overrides preserved in .tausik/stacks/: "
                f"{', '.join(sorted(existing))}"
            )
    else:
        print(
            "  Stack customization: put overrides in .tausik/stacks/<name>/ "
            "(do NOT edit stacks/<name>/ directly — bootstrap overwrites them)"
        )

    # Regenerate MCP tools.py _STACKS_ENUM block from registry. Done in lib_dir
    # (source of truth), so the next copy_mcp picks up the fresh list.
    from bootstrap_stacks import regenerate_mcp_stack_enums

    n_mcp_enums = regenerate_mcp_stack_enums(lib_dir)
    if n_mcp_enums:
        print(f"  MCP stack enums regenerated: {n_mcp_enums} file(s)")

    # Generate IDE-specific files
    if ide == "claude":
        generate_settings_claude(target_dir, project_dir, lib_dir)
        generate_claude_md(project_dir, config.get("project", "my-project"), stacks)
    elif ide == "cursor":
        generate_cursorrules(project_dir, config.get("project", "my-project"), stacks)
    elif ide == "qwen":
        generate_settings_qwen(target_dir, project_dir, venv_python, lib_dir)
        generate_qwen_md(project_dir, config.get("project", "my-project"), stacks)

    # Generate AGENTS.md for OpenCode/Codex (always, regardless of IDE)
    generate_agents_md(project_dir, config.get("project", "my-project"), stacks)

    # Generate shared files
    generate_mcp_json(project_dir, target_dir, venv_python)

    print("  Done!")


def main() -> None:
    # Windows console encoding fix (cp1251/cp1252 can't encode Unicode symbols)
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    parser = argparse.ArgumentParser(description="TAUSIK Bootstrap")
    parser.add_argument(
        "--lib-dir", default=None, help="Library root (default: auto-detect)"
    )
    parser.add_argument(
        "--project-dir", default=None, help="Project root (default: cwd)"
    )
    parser.add_argument(
        "--ide",
        default="claude",
        choices=["claude", "cursor", "qwen", "all"],
        help="Target IDE (default: claude)",
    )
    parser.add_argument(
        "--smart",
        action="store_true",
        default=True,
        help=argparse.SUPPRESS,  # default on since v1.1, kept for backward compat
    )
    parser.add_argument(
        "--no-detect",
        action="store_true",
        help="Skip auto-detection of stacks and skills",
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Interactive skill selection"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )
    parser.add_argument(
        "--update-deps",
        action="store_true",
        help="Force re-download all external dependencies",
    )
    parser.add_argument(
        "--init",
        nargs="?",
        const="",
        default=None,
        metavar="NAME",
        help="Bootstrap + init project (default name: directory name)",
    )
    args = parser.parse_args()

    lib_dir = args.lib_dir or os.path.dirname(_bootstrap_dir)
    project_dir = args.project_dir or os.getcwd()

    print("TAUSIK Bootstrap")
    print(f"  Library: {lib_dir}")
    print(f"  Project: {project_dir}")

    # Load or create config — unified in .tausik/config.json under "bootstrap" key
    tausik_config_path = os.path.join(project_dir, ".tausik", "config.json")
    # Migrate: load from old location if it exists
    old_config_path = os.path.join(
        get_ide_target(project_dir, "claude"), ".tausik-bootstrap.json"
    )
    if os.path.exists(old_config_path) and not os.path.exists(tausik_config_path):
        config = load_config(old_config_path)
    elif os.path.exists(tausik_config_path):
        import json as _json

        try:
            with open(tausik_config_path, encoding="utf-8") as _f:
                full_cfg = _json.load(_f)
        except (_json.JSONDecodeError, OSError) as e:
            print(
                f"  Warning: config corrupted ({tausik_config_path}): {e} — using defaults"
            )
            full_cfg = {}
        config = full_cfg.get("bootstrap", {})
        if not config:
            config = (
                load_config(old_config_path)
                if os.path.exists(old_config_path)
                else dict(DEFAULT_CONFIG)
            )
    else:
        config = dict(DEFAULT_CONFIG)

    # Stack detection
    stacks = detect_stacks(project_dir)
    if stacks:
        print(f"  Stacks detected: {', '.join(stacks)}")
        config["stacks"] = stacks

    # Auto-detect extension skills (default on, --no-detect to skip)
    if args.smart and not args.no_detect:
        ext = detect_extension_skills(project_dir, config.get("core_skills", []))
        if ext:
            print(f"  Extension skills detected: {', '.join(ext)}")
            config["extension_skills"] = ext
    elif args.interactive:
        print("\nAvailable extension skills:")
        for i, skill in enumerate(ALL_EXTENSION_SKILLS, 1):
            print(f"  {i}. {skill}")
        sel = input("Select skills (comma-separated numbers, or 'all'): ").strip()
        if sel.lower() == "all":
            config["extension_skills"] = list(ALL_EXTENSION_SKILLS)
        else:
            indices = [
                int(x.strip()) - 1 for x in sel.split(",") if x.strip().isdigit()
            ]
            config["extension_skills"] = [
                ALL_EXTENSION_SKILLS[i]
                for i in indices
                if 0 <= i < len(ALL_EXTENSION_SKILLS)
            ]

    # IDE selection
    config["ide"] = args.ide

    # Bootstrap
    ides = ["claude", "cursor", "qwen"] if args.ide == "all" else [args.ide]

    if args.dry_run:
        print("\n=== DRY RUN — no files will be written ===")
        for ide in ides:
            target_dir = get_ide_target(project_dir, ide)
            print(f"\n  IDE: {ide} -> {target_dir}")
            all_skills = config.get("core_skills", []) + config.get(
                "extension_skills", []
            )
            print(f"  Skills ({len(all_skills)}): {', '.join(all_skills)}")
            if stacks:
                print(f"  Stacks ({len(stacks)}): {', '.join(stacks)}")
            print("  Will copy: skills/, scripts/, mcp/, references/, roles/, stacks/")
            _generate_map = {
                "claude": "settings.json, CLAUDE.md, .mcp.json",
                "cursor": ".cursorrules, .mcp.json",
                "qwen": "settings.json, QWEN.md, .mcp.json",
            }
            if ide in _generate_map:
                print(f"  Will generate: {_generate_map[ide]}")
        print("\n  Config: .tausik/config.json")
        print("  RAG dir: .tausik/rag/")
        print("  CLI wrapper: .tausik/tausik")
        print("\nNo changes made.")
        return

    # Copy skills.example.json → skills.json if not exists (onboarding)
    skills_json = os.path.join(lib_dir, "skills.json")
    skills_example = os.path.join(lib_dir, "skills.example.json")
    if not os.path.exists(skills_json) and os.path.exists(skills_example):
        import shutil

        shutil.copy2(skills_example, skills_json)
        print(
            "  Copied skills.example.json → skills.json (edit to customize vendor skills)"
        )

    # Vendor dependencies — auto-sync if skills.json exists
    vendor_dir = os.path.join(project_dir, ".tausik", "vendor")
    vendor_skills: dict[str, str] = {}
    manifest = load_skills_json(lib_dir)
    if manifest.get("external_skills"):
        print("\n=== Syncing external dependencies ===")
        dep_results = sync_deps(lib_dir, vendor_dir, force=args.update_deps)
        for name, result in dep_results.items():
            print(f"  {name}: {result['status']}")
    vendor_skills = get_vendor_skill_dirs(vendor_dir)
    if vendor_skills:
        print(f"  Vendor skills available: {', '.join(vendor_skills.keys())}")

    # Create venv and install dependencies
    tausik_dir = os.path.join(project_dir, ".tausik")
    os.makedirs(tausik_dir, exist_ok=True)
    print("\n=== Setting up Python venv ===")
    venv_python = ensure_venv(tausik_dir)
    print(f"  Venv Python: {venv_python}")
    if not install_requirements(tausik_dir, lib_dir):
        print("  WARNING: dependency installation failed. MCP servers may not work.")

    for ide in ides:
        bootstrap_ide(
            lib_dir, project_dir, ide, config, stacks, vendor_skills, venv_python
        )

    # Copy vendor scripts and agents to namespaced subdirs (prevent core overwrites)
    for ide in ides:
        target_dir = get_ide_target(project_dir, ide)
        copy_vendor_assets(vendor_dir, target_dir)

    # Generate skill catalog for agent context
    if manifest.get("external_skills"):
        # Only skills actually copied to .claude/skills/ are ACTIVE
        installed = config.get("core_skills", []) + config.get("extension_skills", [])
        for ide in ides:
            target_dir = get_ide_target(project_dir, ide)
            generate_skill_catalog(target_dir, manifest, installed, vendor_dir)
        print("  Skill catalog generated")

    # RAG setup: create data dir
    rag_dir = os.path.join(project_dir, ".tausik", "rag")
    os.makedirs(rag_dir, exist_ok=True)
    print("\n  RAG: FTS5 mode (keyword search)")

    # Save config, auto-enable gates, clean up old files
    save_tausik_config(
        tausik_config_path,
        config,
        get_lib_commit(lib_dir),
        stacks,
        ides,
        project_dir,
        get_ide_target,
        lib_dir=lib_dir,
    )

    # AGENTS.md is generated by generate_agents_md() per-IDE; lib/AGENTS.md is dogfooding-only.

    from bootstrap_venv import install_cli_wrapper

    install_cli_wrapper(_bootstrap_dir, tausik_dir)
    print("  CLI wrapper: .tausik/tausik (or .tausik/tausik.cmd on Windows)")

    # One-line setup: auto-init if --init provided
    if args.init is not None:
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", os.path.basename(project_dir).lower()).strip(
            "-"
        )
        init_name = args.init or slug or "my-project"
        wrapper_name = "tausik.cmd" if sys.platform == "win32" else "tausik"
        tausik_wrapper = os.path.join(project_dir, ".tausik", wrapper_name)
        try:
            subprocess.run(
                [tausik_wrapper, "init", "--name", init_name],
                cwd=project_dir,
                check=True,
                timeout=30,
            )
            print(f"\nProject '{init_name}' initialized and ready!")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(
                f"\nBootstrap complete but init failed: {e}\n  Run manually: .tausik/tausik init"
            )
    else:
        print("\nBootstrap complete! Run:\n  .tausik/tausik init")


if __name__ == "__main__":
    main()
