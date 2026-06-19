"""TAUSIK CLI handler for `tausik renar` (v16r-conformance-yaml).

`tausik renar conformance` generates a RENAR-CONFORMANCE.yaml self-assessment
whose level is computed from live DB state (§14.4.3), not declared. Prints to
stdout; `--write` persists to RENAR-CONFORMANCE.yaml at the project root.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

from project_config import load_config
from project_service import ProjectService
from renar_conformance import generate
from tausik_utils import utcnow_iso

# Neutral fallback when no assessor can be resolved. Surfaced verbatim in the
# manifest so a self-assessment is never silently attributed to a real person.
FALLBACK_ASSESSOR = "unknown-assessor"


def _git_user_name() -> str | None:
    """Best-effort `git config user.name`. None on any failure (no git, no repo)."""
    try:
        out = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    name = (out.stdout or "").strip()
    return name or None


def resolve_assessor(explicit: str | None, cfg: dict | None = None) -> str:
    """Resolve the conformance assessor id without baking in any personal identity.

    Resolution order: explicit --assessor → config['renar_default_assessor'] →
    git user.name → neutral FALLBACK_ASSESSOR. The fallback is intentional and
    visible: a manifest must never misattribute the self-assessment to a real
    person who did not run it.
    """
    if explicit and explicit.strip():
        return explicit.strip()
    cfg = cfg if cfg is not None else load_config()
    # `or ""` collapses a JSON null (Python None) to "" — a present-but-null
    # config key would otherwise make `cfg.get(key, "")` return None, and
    # str(None) == "None" would be returned as a (fictional) assessor id.
    configured = str(cfg.get("renar_default_assessor") or "").strip()
    if configured:
        return configured
    git_name = _git_user_name()
    if git_name:
        return git_name
    return FALLBACK_ASSESSOR


def _existing_version(path: str) -> int:
    """Read manifest-version from an existing manifest; 0 if absent/unreadable."""
    if not os.path.isfile(path):
        return 0
    try:
        import yaml  # lazy: PyYAML is an optional RENAR dep, not a core CLI dep
    except ModuleNotFoundError:
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return int(data.get("manifest-version", 0))
    except (OSError, ValueError, yaml.YAMLError):
        return 0


def cmd_renar(svc: ProjectService, args: Any) -> None:
    cmd = getattr(args, "renar_cmd", None) or "conformance"
    if cmd == "export":
        _cmd_renar_export(svc, args)
        return
    if cmd != "conformance":
        print(f"Unknown renar subcommand: {cmd!r}")
        return
    assessor = resolve_assessor(getattr(args, "assessor", None))
    date = utcnow_iso()[:10]
    write = getattr(args, "write", False)

    path = None
    manifest_version = 1
    if write:
        from project_config import find_tausik_dir

        root = os.path.dirname(find_tausik_dir())
        path = os.path.join(root, "RENAR-CONFORMANCE.yaml")
        # §14.4.1 immutability: never reset the version. Bump from the existing
        # manifest so each --write is a new version, not a silent overwrite-to-1.
        manifest_version = _existing_version(path) + 1

    manifest, text = generate(svc.be._conn, assessor, date, manifest_version)

    if write and path:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)  # atomic — no partial-write corruption
        print(f"Wrote {path} (manifest-version {manifest_version})")

    level = manifest["level"] or "(none — pre-adoption)"
    print(text)
    print(f"# inferred level: {level} | pre_adoption: {manifest['pre-adoption']}")
    if manifest["assessment-evidence"]["blocked-at"]:
        print(f"# blocked at: {manifest['assessment-evidence']['blocked-at']}")


def _resolve_out_dir(explicit: str | None) -> str:
    """Resolve + safety-check the export target dir.

    Default is <project_root>/renar/. An explicit --out is accepted only if it
    stays strictly inside the project root (assert_export_target) — the write
    path reconciles *.md deletions and must never escape the repo.
    """
    from project_config import find_tausik_dir
    from renar_export import assert_export_target

    project_root = os.path.dirname(find_tausik_dir())
    target = (
        explicit.strip() if (explicit and explicit.strip()) else os.path.join(project_root, "renar")
    )
    return assert_export_target(target, project_root)


def _cmd_renar_export(svc: ProjectService, args: Any) -> None:
    """`tausik renar export [--out renar/] [--check]` — sqlite → derived tree.

    --check exits 1 on drift (stale tree) like `doc constants --check`; the
    default write reconciles deletions and reports written/deleted counts.
    """
    from renar_export import build_tree, check_tree, write_tree

    try:
        out = _resolve_out_dir(getattr(args, "out", None))
    except ValueError as e:
        print(f"renar export: {e}")
        raise SystemExit(1) from e

    tree = build_tree(svc)

    try:
        if getattr(args, "check", False):
            drift = check_tree(out, tree)
            if drift:
                print(f"Drift: {out} does not match live DB state ({len(drift)} issue(s)):")
                for msg in drift:
                    print(f"  {msg}")
                print("  Run: tausik renar export")
                raise SystemExit(1)
            print(f"OK — {out} matches the RENAR artifact store ({len(tree)} file(s)).")
            return

        counts = write_tree(out, tree)
    except OSError as e:
        print(f"renar export failed: {e}")
        raise SystemExit(1) from e

    print(
        f"Exported {counts['written']} file(s) to {out}"
        + (f" (removed {counts['deleted']} stale)" if counts["deleted"] else "")
    )
