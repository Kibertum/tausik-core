#!/usr/bin/env python3
"""TAUSIK bootstrap — generate IDE-specific directory from library sources.

Usage:
    python .tausik-lib/bootstrap/bootstrap.py --ide claude --smart
    python .tausik-lib/bootstrap/bootstrap.py --ide all --smart
"""

from __future__ import annotations

import os
import subprocess
import sys

# Add bootstrap dir to path
_bootstrap_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _bootstrap_dir)
sys.path.insert(0, os.path.join(os.path.dirname(_bootstrap_dir), "scripts"))

from tausik_utils import tausik_config_path  # noqa: E402

from bootstrap_config import (
    ALL_EXTENSION_SKILLS,
    IDE_DIRS,
    SCAFFOLD_IDES,
    detect_extension_skills,
    detect_stacks,
    is_brain_enabled,
    parse_strict_model_profile_env,
    resolve_output_mode,
    save_tausik_config,
)
from bootstrap_modes import (
    resolve_context_tier_or_exit,
    build_parser,
    load_bootstrap_config,
    run_check_mode,
    run_dry_run,
    run_post_bootstrap,
    run_refresh_mode,
)
from bootstrap_copy import (
    copy_aidd_templates,
    copy_mcp,
    copy_references,
    copy_roles,
    copy_scripts,
    copy_skills,
    copy_stacks,
    copy_subagents,
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
from bootstrap_kilo import generate_kilo_commands, generate_kilo_config
from bootstrap_opencode import scaffold_opencode
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


# Module-level alias for existing callers; canonical list is bootstrap_config.IDE_DIRS.
_IDE_DIRS = IDE_DIRS


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
    full_cfg: dict | None = None,
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

    n_subagents = copy_subagents(lib_dir, target_dir, ide)
    if n_subagents:
        print(f"  Sub-agents: {n_subagents} copied")

    n_stacks = copy_stacks(lib_dir, target_dir, ide, stacks)
    print(f"  Stacks: {n_stacks} copied")

    n_aidd = copy_aidd_templates(lib_dir, target_dir)
    if n_aidd:
        print(f"  AIDD templates: {n_aidd} copied")

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

    # output_mode (caveman) compresses agent OUTPUT; orthogonal to tier, bad value → "off".
    # Read from `full_cfg` — the ROOT of .tausik/config.json (where the docs and
    # `context_tier` put it), NOT the nested "bootstrap" `config`: resolving it from
    # there made the documented key a silent no-op (gotcha #207). Keep the two dicts straight.
    proj = config.get("project", "my-project")
    output_mode = resolve_output_mode(full_cfg)

    if ide == "claude":
        generate_settings_claude(target_dir, project_dir, lib_dir)
        generate_claude_md(project_dir, proj, stacks, context_tier, output_mode)
    elif ide == "cursor":
        generate_cursorrules(project_dir, proj, stacks, context_tier, output_mode)
    elif ide == "qwen":
        generate_settings_qwen(target_dir, project_dir, venv_python, lib_dir)
        generate_qwen_md(project_dir, proj, stacks, context_tier, output_mode)
    elif ide == "kilo":
        written = generate_kilo_config(project_dir, target_dir, venv_python, lib_dir, config)
        if written:
            print(f"  Kilo MCP config: {len(written)} file(s) — {', '.join(written)}")
        else:
            print("  Kilo MCP config: skipped (no server.py found)")
        n_cmds = generate_kilo_commands(target_dir)
        if n_cmds:
            print(f"  Kilo commands: {n_cmds} stub(s)")
    elif ide == "opencode":
        scaffold_opencode(
            project_dir,
            target_dir,
            venv_python,
            lib_dir,
            config,
            stacks,
            context_tier,
            output_mode,
        )

    # AGENTS.md for every host EXCEPT OpenCode: OpenCode merges `instructions`
    # INTO AGENTS.md (shipping both doubles the rule body — the very context
    # bloat this work fixes), and its first-match-wins would prefer the user's.
    if ide != "opencode":
        generate_agents_md(project_dir, proj, stacks, context_tier, output_mode)

    if ide == "cursor":
        generate_cursor_mcp_json(project_dir, target_dir, venv_python)

    print("  Done!")


def main() -> None:
    # Single source of truth for UTF-8 stdio (Windows cp1251 crashes on Cyrillic
    # output). bootstrap runs directly (not via the CLI wrapper) so it must
    # self-protect — same guard every other entry point uses.
    from tausik_utils import fix_stdio_encoding

    fix_stdio_encoding()

    args = build_parser().parse_args()

    lib_dir = args.lib_dir or os.path.dirname(_bootstrap_dir)
    project_dir = args.project_dir or os.getcwd()

    print("TAUSIK Bootstrap")
    print(f"  Library: {lib_dir}")
    print(f"  Project: {project_dir}")

    config, full_cfg = load_bootstrap_config(project_dir, get_ide_target)
    config_path = tausik_config_path(project_dir)

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

    ides = list(SCAFFOLD_IDES) if args.ide == "all" else [args.ide]

    try:
        env_profile_slug = parse_strict_model_profile_env()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        run_check_mode(lib_dir, project_dir, ides)
        return

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

    context_tier = resolve_context_tier_or_exit(config_path)

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
            full_cfg=full_cfg,
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
            config_path,
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
