"""Bootstrap argparse + dry-run + refresh path.

Extracted from bootstrap.py to keep that orchestrator under the 400-line
filesize gate (v14b-followup-bootstrap-py-filesize-debt). Public CLI
surface (`python bootstrap/bootstrap.py --update / --init / --dry-run`)
is unchanged — bootstrap.py imports these helpers and dispatches.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Callable

from bootstrap_config import (
    SCAFFOLD_IDES,
    TAUSIK_MODEL_PROFILE_ENV,
    save_tausik_config,
)

# scripts/ injected on sys.path by bootstrap.py top-level; safe to import here.
from tausik_utils import tausik_config_path


def build_parser() -> argparse.ArgumentParser:
    """Build the bootstrap CLI argparse parser."""
    parser = argparse.ArgumentParser(description="TAUSIK Bootstrap")
    parser.add_argument("--lib-dir", default=None, help="Library root (default: auto-detect)")
    parser.add_argument("--project-dir", default=None, help="Project root (default: cwd)")
    parser.add_argument(
        "--ide",
        default="claude",
        choices=[*SCAFFOLD_IDES, "all"],
        help="Target IDE (default: claude)",
    )
    parser.add_argument(
        "--smart",
        action="store_true",
        default=True,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-detect",
        action="store_true",
        help="Skip auto-detection of stacks and skills",
    )
    parser.add_argument("--interactive", action="store_true", help="Interactive skill selection")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Rewrite .tausik/config.json from bootstrap state + env (no IDE skill/script copy)",
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
    parser.add_argument(
        "--include-official",
        action="store_true",
        help=(
            "Include skills-official/registry.json stubs in the deployed set. "
            "Default since v1.4: only source harness/skills/ are deployed (12 + brain "
            "conditional). Use this flag to restore the larger pre-v1.4 skill list."
        ),
    )
    parser.add_argument(
        "--include-vendor",
        action="store_true",
        help="Alias for --include-official (legacy compat).",
    )
    return parser


def run_dry_run(
    config: dict,
    stacks: list[str],
    ides: list[str],
    env_profile_slug: str | None,
    project_dir: str,
    get_ide_target: Callable[[str, str], str],
) -> None:
    """Show what would be done without writing files. Returns to caller."""
    print("\n=== DRY RUN — no files will be written ===")
    for ide in ides:
        target_dir = get_ide_target(project_dir, ide)
        print(f"\n  IDE: {ide} -> {target_dir}")
        all_skills = config.get("core_skills", []) + config.get("extension_skills", [])
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
    if env_profile_slug:
        print(f"  {TAUSIK_MODEL_PROFILE_ENV} → top-level model_profile={env_profile_slug!r}")
    print("  RAG dir: .tausik/rag/")
    print("  CLI wrapper: .tausik/tausik")
    print("\nNo changes made.")


def run_refresh_mode(
    project_dir: str,
    lib_dir: str,
    config: dict,
    stacks: list[str],
    ides: list[str],
    bootstrap_dir: str,
    get_lib_commit: Callable[[str], str | None],
    get_ide_target: Callable[[str, str], str],
) -> None:
    """Rewrite .tausik/config.json from bootstrap state without copying skills/scripts."""
    tausik_dir = os.path.join(project_dir, ".tausik")
    os.makedirs(tausik_dir, exist_ok=True)
    config_path = tausik_config_path(project_dir)
    _scripts = os.path.join(lib_dir, "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
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

    install_cli_wrapper(bootstrap_dir, tausik_dir)
    print("\n=== Refresh complete ===")
    print("  Updated .tausik/config.json only (no skills/scripts/MCP copy).")
    print("  CLI wrapper: .tausik/tausik (or .tausik/tausik.cmd on Windows)")


def run_post_bootstrap(
    args: Any,
    project_dir: str,
) -> None:
    """Post-bootstrap: optionally invoke `tausik init` and prompt for Brain setup."""
    import subprocess

    if args.init is not None:
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", os.path.basename(project_dir).lower()).strip("-")
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
            print(f"\nBootstrap complete but init failed: {e}\n  Run manually: .tausik/tausik init")
    else:
        already_init = os.path.isfile(os.path.join(project_dir, ".tausik", "tausik.db"))
        if already_init:
            print(
                "\nBootstrap complete — project DB already exists. "
                "Try: `.tausik/tausik status` / `.tausik/tausik doctor`"
            )
        else:
            print("\nBootstrap complete! Run:\n  .tausik/tausik init")

    # Brain wizard runs only when interactive AND project was just initialised:
    # brain init writes into the project DB.
    if args.interactive and args.init is not None:
        try:
            answer = (
                input("\nSetup Shared Brain (cross-project knowledge in Notion)? [y/N] ")
                .strip()
                .lower()
            )
        except EOFError:
            answer = ""
        if answer in ("y", "yes"):
            wrapper_name = "tausik.cmd" if sys.platform == "win32" else "tausik"
            tausik_wrapper = os.path.join(project_dir, ".tausik", wrapper_name)
            try:
                subprocess.run(
                    [tausik_wrapper, "brain", "init"],
                    cwd=project_dir,
                    check=False,
                )
            except FileNotFoundError as e:
                print(
                    f"  Could not launch brain init wizard: {e}\n"
                    "  Run manually later: .tausik/tausik brain init"
                )
        else:
            print("  Skipping Shared Brain setup. Run later with `.tausik/tausik brain init`.")


def load_bootstrap_config(
    project_dir: str,
    get_ide_target: Callable[[str, str], str],
) -> tuple[dict, dict[str, Any]]:
    """Load bootstrap config from .tausik/config.json with legacy fallback.

    Returns (bootstrap_section, full_config). full_config is empty dict when
    only the legacy file exists or no config exists.
    """
    from bootstrap_config import DEFAULT_CONFIG, load_config

    config_path = tausik_config_path(project_dir)
    old_config_path = os.path.join(get_ide_target(project_dir, "claude"), ".tausik-bootstrap.json")
    full_cfg: dict[str, Any] = {}
    if os.path.exists(old_config_path) and not os.path.exists(config_path):
        return load_config(old_config_path), full_cfg
    if os.path.exists(config_path):
        import json as _json

        try:
            with open(config_path, encoding="utf-8") as _f:
                full_cfg = _json.load(_f)
        except (_json.JSONDecodeError, OSError) as e:
            print(f"  Warning: config corrupted ({config_path}): {e} — using defaults")
            full_cfg = {}
        config = full_cfg.get("bootstrap", {})
        if not config:
            config = (
                load_config(old_config_path)
                if os.path.exists(old_config_path)
                else dict(DEFAULT_CONFIG)
            )
        return config, full_cfg
    return dict(DEFAULT_CONFIG), full_cfg


def resolve_context_tier_or_exit(config_path: str) -> str:
    """Read the config ROOT and return its ``context_tier``, or exit(1) on a bad value.

    Both root-level rule knobs are resolved from the same file: this one raises-then-exits
    (an unknown tier is a typo worth stopping for), while ``resolve_output_mode`` falls back
    to ``off``. Kept beside it so the two contracts are visible together — and so callers
    cannot accidentally hand either of them the nested "bootstrap" section (gotcha #207).
    """
    import json
    import sys

    cfg: dict = {}
    if os.path.isfile(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            cfg = {}
    from project_config import resolve_context_tier

    try:
        return resolve_context_tier(cfg)
    except ValueError as exc:
        print(f"Error: {exc} (file: {config_path})")
        sys.exit(1)
