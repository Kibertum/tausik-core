#!/usr/bin/env python3
"""TAUSIK bootstrap — generate IDE-specific directory from library sources.

Usage:
    python .tausik-lib/bootstrap/bootstrap.py --ide claude --smart
    python .tausik-lib/bootstrap/bootstrap.py --ide cursor
    python .tausik-lib/bootstrap/bootstrap.py --ide all --smart
"""

from __future__ import annotations

import os
import subprocess
import sys

# Add bootstrap dir to path
_bootstrap_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _bootstrap_dir)

from bootstrap_config import (
    ALL_EXTENSION_SKILLS,
    detect_extension_skills,
    detect_stacks,
    is_brain_enabled,
    parse_strict_model_profile_env,
    save_tausik_config,
)
from bootstrap_modes import (
    build_parser,
    load_bootstrap_config,
    run_dry_run,
    run_post_bootstrap,
    run_refresh_mode,
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
    generate_cursor_mcp_json,
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
    context_tier: str = "standard",
    *,
    include_official_stubs: bool = False,
    brain_enabled: bool = True,
) -> None:
    """Bootstrap for a single IDE."""
    target_dir = get_ide_target(project_dir, ide)
    os.makedirs(target_dir, exist_ok=True)
    print(f"\n=== Bootstrapping for {ide} -> {target_dir} ===")

    n_skills = copy_skills(
        lib_dir,
        target_dir,
        config,
        ide,
        vendor_skills,
        include_official_stubs=include_official_stubs,
        brain_enabled=brain_enabled,
    )
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

    from bootstrap_stacks import regenerate_mcp_stack_enums

    n_mcp_enums = regenerate_mcp_stack_enums(lib_dir)
    if n_mcp_enums:
        print(f"  MCP stack enums regenerated: {n_mcp_enums} file(s)")

    if ide == "claude":
        generate_settings_claude(target_dir, project_dir, lib_dir)
        generate_claude_md(project_dir, config.get("project", "my-project"), stacks, context_tier)
    elif ide == "cursor":
        generate_cursorrules(project_dir, config.get("project", "my-project"), stacks, context_tier)
    elif ide == "qwen":
        generate_settings_qwen(target_dir, project_dir, venv_python, lib_dir)
        generate_qwen_md(project_dir, config.get("project", "my-project"), stacks, context_tier)

    generate_agents_md(project_dir, config.get("project", "my-project"), stacks, context_tier)

    if ide == "cursor":
        generate_cursor_mcp_json(project_dir, target_dir, venv_python)

    print("  Done!")


def main() -> None:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    args = build_parser().parse_args()

    lib_dir = args.lib_dir or os.path.dirname(_bootstrap_dir)
    project_dir = args.project_dir or os.getcwd()

    print("TAUSIK Bootstrap")
    print(f"  Library: {lib_dir}")
    print(f"  Project: {project_dir}")

    config, full_cfg = load_bootstrap_config(project_dir, get_ide_target)
    tausik_config_path = os.path.join(project_dir, ".tausik", "config.json")

    # v14b-skill-core-cleanup gating decisions (computed once, passed per IDE).
    include_official_stubs = bool(args.include_official or args.include_vendor)
    brain_enabled = is_brain_enabled(full_cfg)
    if not brain_enabled:
        print("  brain: skipped (Notion not configured — `tausik brain init` to enable)")
    if not include_official_stubs:
        print("  Official-skill stubs: opt-in (use --include-official to deploy them)")

    stacks = detect_stacks(project_dir)
    if stacks:
        print(f"  Stacks detected: {', '.join(stacks)}")
        config["stacks"] = stacks

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
            indices = [int(x.strip()) - 1 for x in sel.split(",") if x.strip().isdigit()]
            config["extension_skills"] = [
                ALL_EXTENSION_SKILLS[i] for i in indices if 0 <= i < len(ALL_EXTENSION_SKILLS)
            ]

    config["ide"] = args.ide

    ides = ["claude", "cursor", "qwen"] if args.ide == "all" else [args.ide]

    try:
        env_profile_slug = parse_strict_model_profile_env()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        run_dry_run(config, stacks, ides, env_profile_slug, project_dir, get_ide_target)
        return

    if args.refresh:
        run_refresh_mode(
            project_dir,
            lib_dir,
            config,
            stacks,
            ides,
            _bootstrap_dir,
            get_lib_commit,
            get_ide_target,
        )
        return

    skills_json = os.path.join(lib_dir, "skills.json")
    skills_example = os.path.join(lib_dir, "skills.example.json")
    if not os.path.exists(skills_json) and os.path.exists(skills_example):
        import shutil

        shutil.copy2(skills_example, skills_json)
        print("  Copied skills.example.json → skills.json (edit to customize vendor skills)")

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

    tausik_dir = os.path.join(project_dir, ".tausik")
    os.makedirs(tausik_dir, exist_ok=True)
    print("\n=== Setting up Python venv ===")
    venv_python = ensure_venv(tausik_dir)
    print(f"  Venv Python: {venv_python}")
    if not install_requirements(tausik_dir, lib_dir):
        print("  WARNING: dependency installation failed. MCP servers may not work.")

    _scripts = os.path.join(lib_dir, "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    import json as _json_ct

    _cfg_for_tier: dict = {}
    if os.path.isfile(tausik_config_path):
        try:
            with open(tausik_config_path, encoding="utf-8") as _cf:
                _cfg_for_tier = _json_ct.load(_cf)
        except (_json_ct.JSONDecodeError, OSError):
            _cfg_for_tier = {}
    from project_config import resolve_context_tier

    try:
        context_tier = resolve_context_tier(_cfg_for_tier)
    except ValueError as exc:
        print(f"Error: {exc} (file: {tausik_config_path})")
        sys.exit(1)

    for ide in ides:
        bootstrap_ide(
            lib_dir,
            project_dir,
            ide,
            config,
            stacks,
            vendor_skills,
            venv_python,
            context_tier,
            include_official_stubs=include_official_stubs,
            brain_enabled=brain_enabled,
        )

    if "claude" in ides:
        generate_mcp_json(project_dir, get_ide_target(project_dir, "claude"), venv_python)
    else:
        generate_mcp_json(project_dir, get_ide_target(project_dir, ides[0]), venv_python)

    for ide in ides:
        target_dir = get_ide_target(project_dir, ide)
        copy_vendor_assets(vendor_dir, target_dir)

    if manifest.get("external_skills"):
        installed = config.get("core_skills", []) + config.get("extension_skills", [])
        for ide in ides:
            target_dir = get_ide_target(project_dir, ide)
            generate_skill_catalog(target_dir, manifest, installed, vendor_dir)
        print("  Skill catalog generated")

    rag_dir = os.path.join(project_dir, ".tausik", "rag")
    os.makedirs(rag_dir, exist_ok=True)
    print("\n  RAG: FTS5 mode (keyword search)")

    try:
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
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    from bootstrap_venv import install_cli_wrapper

    install_cli_wrapper(_bootstrap_dir, tausik_dir)
    print("  CLI wrapper: .tausik/tausik (or .tausik/tausik.cmd on Windows)")

    run_post_bootstrap(args, project_dir)


if __name__ == "__main__":
    main()
