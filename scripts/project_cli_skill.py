"""CLI dispatcher for `tausik skill ...` (lifecycle, catalog, repo, rebuild).

Extracted from project_cli_extra.py to keep that file under the 400-line gate.
"""

from __future__ import annotations

import json
import os
from typing import Any

from project_service import ProjectService
from tausik_utils import tausik_config_path


def cmd_skill(svc: ProjectService, args: Any) -> None:
    """Handle skill lifecycle: activate, deactivate, list, install, uninstall, repo."""
    c = getattr(args, "skill_cmd", None)
    project_dir = os.getcwd()
    vendor_dir = os.path.join(project_dir, ".tausik", "vendor")
    tausik_dir = os.path.join(project_dir, ".tausik")
    try:
        from ide_utils import detect_ide, get_agents_skills_dir, get_skills_dir

        _ide = detect_ide(project_dir)
        skills_dst = get_skills_dir(project_dir, _ide)
        lib_skills_dir = get_agents_skills_dir(project_dir, _ide)
    except ImportError:
        skills_dst = os.path.join(project_dir, ".claude", "skills")
        lib_skills_dir = os.path.join(project_dir, "harness", "claude", "skills")

    config_path = tausik_config_path(project_dir)

    if c == "activate":
        print(svc.skill_activate(args.name, vendor_dir, skills_dst, lib_skills_dir, config_path))
    elif c == "deactivate":
        print(svc.skill_deactivate(args.name, skills_dst, lib_skills_dir, config_path))
    elif c == "list":
        _print_skill_list(svc, vendor_dir, skills_dst)
    elif c == "install":
        print(svc.skill_install(args.name, vendor_dir, skills_dst, config_path, tausik_dir))
    elif c == "uninstall":
        print(svc.skill_uninstall(args.name, skills_dst, config_path))
    elif c == "repo":
        _cmd_skill_repo(args, vendor_dir, config_path)
    elif c == "catalog":
        _cmd_skill_catalog(svc, args, vendor_dir, config_path)
    elif c == "rebuild":
        from project_cli_config import cmd_skill_rebuild

        cmd_skill_rebuild(args, project_dir, skills_dst)
    elif c == "bundle":
        _cmd_skill_bundle(svc, args, vendor_dir, skills_dst, config_path, tausik_dir)
    elif c == "sign":
        _cmd_skill_sign(args, project_dir)
    else:
        print(
            "Usage: tausik skill [activate|deactivate|list|install|uninstall|repo|catalog|rebuild|bundle|sign]"
        )


def _cmd_skill_sign(args: Any, project_dir: str) -> None:
    """`tausik skill sign <dir>` — supply-chain signature for a release dir."""
    import sys

    from supply_sign import SupplySignError, sign_artifact

    try:
        info = sign_artifact(project_dir, args.path, name=getattr(args, "name", None))
    except SupplySignError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    print(
        f"Signed '{info['name']}' ({info['files']} files).\n"
        f"  signature:   {info['path']}\n"
        f"  fingerprint: {info['key_fingerprint']}\n"
        "Ship the directory as-is; installers verify it against your "
        "public key (tausik key show)."
    )


def _cmd_skill_bundle(
    svc: ProjectService,
    args: Any,
    vendor_dir: str,
    skills_dst: str,
    config_path: str,
    tausik_dir: str,
) -> None:
    """Dispatch `tausik skill bundle [list|show|install|uninstall]`."""
    import skill_bundles

    sub = getattr(args, "bundle_cmd", None)
    skills_official = _resolve_skills_official_dir()

    if sub == "list":
        try:
            entries = skill_bundles.bundle_list(skills_official)
        except skill_bundles.BundleError as exc:
            print(f"Error: {exc}")
            return
        if getattr(args, "as_json", False):
            print(json.dumps(entries, ensure_ascii=False, indent=2))
            return
        print(skill_bundles.format_list_table(entries))
        return

    if sub == "show":
        try:
            entry = skill_bundles.bundle_show(args.name, skills_official)
        except skill_bundles.BundleError as exc:
            print(f"Error: {exc}")
            return
        if getattr(args, "as_json", False):
            print(json.dumps(entry, ensure_ascii=False, indent=2))
            return
        print(skill_bundles.format_show(entry))
        return

    if sub == "install":

        def _install_one(name: str) -> str:
            return svc.skill_install(name, vendor_dir, skills_dst, config_path, tausik_dir)

        try:
            results = skill_bundles.bundle_install(args.name, skills_official, _install_one)
        except skill_bundles.BundleError as exc:
            print(f"Error: {exc}")
            return
        if getattr(args, "as_json", False):
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        print(f"Installing bundle '{args.name}':")
        print(skill_bundles.format_install_results(results))
        return

    if sub == "uninstall":

        def _uninstall_one(name: str) -> str:
            return svc.skill_uninstall(name, skills_dst, config_path)

        try:
            results = skill_bundles.bundle_uninstall(args.name, skills_official, _uninstall_one)
        except skill_bundles.BundleError as exc:
            print(f"Error: {exc}")
            return
        if getattr(args, "as_json", False):
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        print(f"Uninstalling bundle '{args.name}':")
        print(skill_bundles.format_install_results(results))
        return

    print("Usage: tausik skill bundle [list|show|install|uninstall] [--json]")


def _resolve_skills_official_dir() -> str:
    """Locate skills-official/ — repo root in dev, lib_dir in installed projects."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(here), "skills-official"),
        os.path.join(here, "..", "..", "skills-official"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return os.path.abspath(path)
    return candidates[0]


def _print_skill_list(svc: ProjectService, vendor_dir: str, skills_dst: str) -> None:
    data = svc.skill_list(vendor_dir, skills_dst)
    print("Skills:")
    for s in sorted(data["active"], key=lambda x: x["name"]):
        print(f"  [ACTIVE  ] {s['name']}")
    for s in sorted(data["vendored"], key=lambda x: x["name"]):
        print(f"  [VENDORED] {s['name']}")
    try:
        from skill_repos import repo_list_all_skills

        active_names = {s["name"] for s in data["active"]}
        vendored_names = {s["name"] for s in data["vendored"]}
        all_repo_skills = repo_list_all_skills(vendor_dir)
        for s in all_repo_skills:
            if s["name"] not in active_names and s["name"] not in vendored_names:
                desc = f" — {s['description']}" if s.get("description") else ""
                print(f"  [AVAILABLE] {s['name']} ({s['repo']}){desc}")
    except ImportError:
        all_repo_skills = []
    if not data["active"] and not data["vendored"] and not all_repo_skills:
        print("  (none)")


def _cmd_skill_catalog(svc: ProjectService, args: Any, vendor_dir: str, config_path: str) -> None:
    """Print discovery catalog: name / category / repo / description."""
    repo_name = getattr(args, "repo", None)
    rows = svc.skill_catalog(vendor_dir, repo_name=repo_name, config_path=config_path)
    if getattr(args, "as_json", False):
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    if not rows:
        if repo_name:
            print(f"  (no skills found in repo '{repo_name}')")
        else:
            print("  (no skill repos cloned — try `tausik skill repo add <url>`)")
        return
    name_w = max(len("name"), max(len(r["name"]) for r in rows))
    cat_w = max(len("category"), max(len(r.get("category") or "") for r in rows))
    repo_w = max(len("repo"), max(len(r["repo"]) for r in rows))
    print(f"  {'name':<{name_w}}  {'category':<{cat_w}}  {'repo':<{repo_w}}  description")
    print(f"  {'-' * name_w}  {'-' * cat_w}  {'-' * repo_w}  -----------")
    for r in rows:
        cat = r.get("category") or ""
        desc = (r.get("description") or "").splitlines()[0][:80]
        print(f"  {r['name']:<{name_w}}  {cat:<{cat_w}}  {r['repo']:<{repo_w}}  {desc}")


def _cmd_skill_repo(args: Any, vendor_dir: str, config_path: str) -> None:
    """Handle skill repo subcommands."""
    try:
        from skill_repos import repo_add, repo_list, repo_remove
    except ImportError:
        print("Error: skill_repos module not found. Run bootstrap first.")
        return

    rc = getattr(args, "repo_cmd", None)
    if rc == "add":
        print(
            repo_add(
                args.url,
                vendor_dir,
                config_path,
                force=getattr(args, "force", False),
            )
        )
    elif rc == "remove":
        print(repo_remove(args.name, vendor_dir, config_path))
    elif rc == "trust":
        import sys

        from skill_manager import SkillManagerError
        from skill_repos import update_config_repo_trust

        try:
            update_config_repo_trust(config_path, args.name, args.pubkey)
        except SkillManagerError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)
        print(
            f"Pinned publisher key for repo '{args.name}'. Signed skills from "
            "it are now verified on install; mismatches are refused."
        )
    elif rc == "list":
        from skill_repos import get_repo_pinned_pubkey

        repos = repo_list(vendor_dir, config_path)
        if not repos:
            print("No skill repos configured.")
            print("  Add one: tausik skill repo add <git-url>")
            return
        print("Skill repos:")
        for r in repos:
            status = "cloned" if r["cloned"] else "not cloned"
            default = " (default)" if r.get("default") else ""
            trusted = (
                " [trusted key pinned]" if get_repo_pinned_pubkey(config_path, r["name"]) else ""
            )
            print(f"  {r['name']}{default} [{status}]{trusted} — {r['url']}")
            if r["skills"]:
                print(f"    Skills: {', '.join(r['skills'])}")
    else:
        print("Usage: tausik skill repo [add|remove|list|trust]")
