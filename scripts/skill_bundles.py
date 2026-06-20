"""TAUSIK skill bundles -- logical grouping of vendor skills via bundles.json.

Bundles are a discovery + bulk-install layer on top of the existing
single-skill install pipeline. The physical layout in skills-official/ stays
flat (each skill at top level) for backward compat with `tausik skill install
<name>`. bundles.json maps a bundle name to a list of skill names.

Public API (used by CLI handler):
    load_bundles_manifest(skills_official_dir, *, manifest_path=None)
    bundle_list(skills_official_dir) -> list[dict]
    bundle_show(name, skills_official_dir) -> dict
    bundle_install(name, skills_official_dir, install_one) -> list[dict]
    bundle_uninstall(name, skills_official_dir, uninstall_one) -> list[dict]

`install_one(name) -> str` and `uninstall_one(name) -> str` are passed in by
the caller so this module stays free of skill_manager / project_service
imports (testable in isolation, no clone-side-effects).
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

DEFAULT_MANIFEST = "bundles.json"


class BundleError(Exception):
    """Raised on missing manifest, unknown bundle, or schema violation."""


# ---------------------------------------------------------------------------
# Manifest loading + validation
# ---------------------------------------------------------------------------


def _manifest_path(skills_official_dir: str, override: str | None) -> str:
    if override:
        return override
    return os.path.join(skills_official_dir, DEFAULT_MANIFEST)


def load_bundles_manifest(
    skills_official_dir: str, *, manifest_path: str | None = None
) -> dict[str, Any]:
    """Load and validate bundles.json. Returns the parsed dict on success.

    Raises:
        BundleError: missing file, malformed JSON, or schema violation.
    """
    path = _manifest_path(skills_official_dir, manifest_path)
    if not os.path.isfile(path):
        raise BundleError(
            f"No bundles manifest at {path}. "
            f"Bundle commands require skills-official/bundles.json — "
            f"see docs/en/skill-bundles.md."
        )
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleError(f"Cannot parse {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise BundleError(f"{path} root must be a JSON object, got {type(data).__name__}")
    bundles = data.get("bundles")
    if not isinstance(bundles, dict):
        raise BundleError(f"{path} must contain a 'bundles' object")
    for name, body in bundles.items():
        if not isinstance(body, dict):
            raise BundleError(f"bundle {name!r} must be an object")
        skills = body.get("skills")
        if skills is not None and not isinstance(skills, list):
            raise BundleError(f"bundle {name!r}.skills must be a list")
    return data


def _bundle_body(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    bundles = manifest.get("bundles", {})
    if name not in bundles:
        raise BundleError(
            f"Unknown bundle {name!r}. Run `tausik skill bundle list` to see available bundles."
        )
    body: dict[str, Any] = bundles[name]
    return body


def deprecated_skills(manifest: dict[str, Any]) -> dict[str, str]:
    """Map of deprecated_skill_name -> migration_message. Empty if not declared."""
    dep = manifest.get("deprecated") or {}
    if not isinstance(dep, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in dep.items():
        if k.startswith("_"):
            continue
        if isinstance(v, str):
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def bundle_list(
    skills_official_dir: str, *, manifest_path: str | None = None
) -> list[dict[str, Any]]:
    """Summarize every bundle: name, title, skill count, placeholder flag."""
    manifest = load_bundles_manifest(skills_official_dir, manifest_path=manifest_path)
    out: list[dict[str, Any]] = []
    for name, body in manifest.get("bundles", {}).items():
        skills = body.get("skills") or []
        out.append(
            {
                "name": name,
                "title": body.get("title", name),
                "description": body.get("description", ""),
                "skill_count": len(skills),
                "placeholder": bool(body.get("placeholder", False)),
            }
        )
    return out


def bundle_show(
    name: str, skills_official_dir: str, *, manifest_path: str | None = None
) -> dict[str, Any]:
    """Full body for a single bundle: title, description, skills list."""
    manifest = load_bundles_manifest(skills_official_dir, manifest_path=manifest_path)
    body = _bundle_body(manifest, name)
    return {
        "name": name,
        "title": body.get("title", name),
        "description": body.get("description", ""),
        "skills": list(body.get("skills") or []),
        "placeholder": bool(body.get("placeholder", False)),
    }


# ---------------------------------------------------------------------------
# Bulk install / uninstall
# ---------------------------------------------------------------------------


def bundle_install(
    name: str,
    skills_official_dir: str,
    install_one: Callable[[str], str],
    *,
    manifest_path: str | None = None,
) -> list[dict[str, str]]:
    """Install every skill in the bundle. Each call routes through `install_one`.

    Returns a list of {skill, status, message} entries — `status` is one of
    'installed', 'deprecated_skipped', 'error'. Continues on per-skill error.
    """
    manifest = load_bundles_manifest(skills_official_dir, manifest_path=manifest_path)
    body = _bundle_body(manifest, name)
    if body.get("placeholder"):
        return [{"skill": "", "status": "placeholder", "message": "Bundle is empty (placeholder)."}]
    deprecated = deprecated_skills(manifest)
    results: list[dict[str, str]] = []
    for skill in body.get("skills") or []:
        if skill in deprecated:
            results.append(
                {
                    "skill": skill,
                    "status": "deprecated_skipped",
                    "message": f"deprecated: {deprecated[skill]}",
                }
            )
            continue
        try:
            msg = install_one(skill)
            results.append({"skill": skill, "status": "installed", "message": str(msg)})
        except Exception as exc:  # noqa: BLE001
            results.append({"skill": skill, "status": "error", "message": str(exc)})
    return results


def bundle_uninstall(
    name: str,
    skills_official_dir: str,
    uninstall_one: Callable[[str], str],
    *,
    manifest_path: str | None = None,
) -> list[dict[str, str]]:
    """Uninstall every skill in the bundle via `uninstall_one`. Continues on error."""
    manifest = load_bundles_manifest(skills_official_dir, manifest_path=manifest_path)
    body = _bundle_body(manifest, name)
    if body.get("placeholder"):
        return [{"skill": "", "status": "placeholder", "message": "Bundle is empty (placeholder)."}]
    results: list[dict[str, str]] = []
    for skill in body.get("skills") or []:
        try:
            msg = uninstall_one(skill)
            results.append({"skill": skill, "status": "uninstalled", "message": str(msg)})
        except Exception as exc:  # noqa: BLE001
            results.append({"skill": skill, "status": "error", "message": str(exc)})
    return results


# ---------------------------------------------------------------------------
# Pretty-print helpers (used by CLI)
# ---------------------------------------------------------------------------


def format_list_table(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "No bundles configured."
    width = max((len(e["name"]) for e in entries), default=10)
    lines = [f"{'Bundle':<{width}}  Skills  Title"]
    lines.append(f"{'-' * width}  ------  -----")
    for e in entries:
        marker = " (placeholder)" if e["placeholder"] else ""
        lines.append(f"{e['name']:<{width}}  {e['skill_count']:>6}  {e['title']}{marker}")
    return "\n".join(lines)


def format_show(entry: dict[str, Any]) -> str:
    lines = [f"Bundle: {entry['name']} — {entry['title']}"]
    if entry.get("description"):
        lines.append(entry["description"])
    if entry["placeholder"]:
        lines.append("(empty placeholder)")
    elif entry["skills"]:
        lines.append("Skills:")
        for s in entry["skills"]:
            lines.append(f"  - {s}")
    else:
        lines.append("No skills declared.")
    return "\n".join(lines)


def format_install_results(results: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for r in results:
        if r["status"] == "placeholder":
            lines.append(r["message"])
            continue
        prefix = {"installed": "[OK]", "uninstalled": "[OK]", "deprecated_skipped": "[SKIP]"}.get(
            r["status"], "[ERR]"
        )
        lines.append(f"  {prefix} {r['skill']}: {r['message']}")
    return "\n".join(lines) if lines else "(no skills)"
