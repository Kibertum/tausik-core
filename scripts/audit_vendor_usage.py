"""Audit vendor skill repos for cleanup candidates.

Re-scoped from telemetry-based usage tracking (usage_events tracks tokens,
not skill invocations) to static cross-check of vendor_dir vs config's
``installed_skills`` list, plus file mtime as a weak activity proxy.

Public API:
    audit_vendor_usage(vendor_dir, config_path) -> dict

Returns:
    {
      "installed": [{"name", "skills": [...], "last_modified_iso"}, ...],
      "vendored_unused": [{"name", "cloned_at_iso", "skills": [...]}, ...],
      "unknown": [{"name", "reason"}, ...],
    }

Never raises. Surfaces errors per-vendor in the ``unknown`` bucket.
The audit is read-only — no deletes, no writes. User reviews and decides.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


def _list_vendor_dirs(vendor_dir: str) -> list[str]:
    if not os.path.isdir(vendor_dir):
        return []
    return sorted(d for d in os.listdir(vendor_dir) if os.path.isdir(os.path.join(vendor_dir, d)))


def _vendor_skills(vendor_path: str) -> list[str]:
    """Skills offered by a vendor: subdirs containing SKILL.md."""
    out: list[str] = []
    try:
        for entry in sorted(os.listdir(vendor_path)):
            full = os.path.join(vendor_path, entry)
            if entry in ("scripts", "agents", "__pycache__"):
                continue
            if os.path.isdir(full) and os.path.isfile(os.path.join(full, "SKILL.md")):
                out.append(entry)
    except OSError:
        pass
    return out


def _vendor_last_mtime_iso(vendor_path: str) -> str | None:
    """Newest mtime across vendor's tree, as a weak 'last touched' proxy."""
    newest: float = 0.0
    try:
        for root, _dirs, files in os.walk(vendor_path):
            for f in files:
                full = os.path.join(root, f)
                try:
                    mt = os.path.getmtime(full)
                    if mt > newest:
                        newest = mt
                except OSError:
                    continue
    except OSError:
        return None
    if newest == 0.0:
        return None
    return datetime.fromtimestamp(newest, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_installed(config_path: str) -> set[str]:
    if not os.path.isfile(config_path):
        return set()
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return set()
        installed = data.get("installed_skills") or []
        if not isinstance(installed, list):
            return set()
        return {str(x) for x in installed if isinstance(x, str)}
    except (OSError, json.JSONDecodeError):
        return set()


def audit_vendor_usage(vendor_dir: str, config_path: str) -> dict[str, list[Any]]:
    """Classify each vendor under ``vendor_dir`` as installed / vendored_unused / unknown.

    A vendor is **installed** if at least one of its declared skills appears
    in the project's ``installed_skills`` list. Otherwise it is
    **vendored_unused** — a candidate for ``tausik skill repo remove``.
    Read errors land in ``unknown``.
    """
    installed = _read_installed(config_path)
    out: dict[str, list[Any]] = {"installed": [], "vendored_unused": [], "unknown": []}

    for name in _list_vendor_dirs(vendor_dir):
        vendor_path = os.path.join(vendor_dir, name)
        try:
            skills = _vendor_skills(vendor_path)
        except Exception as e:  # noqa: BLE001
            out["unknown"].append({"name": name, "reason": f"skill enumeration failed: {e}"})
            continue
        last_mt = _vendor_last_mtime_iso(vendor_path)
        if any(s in installed for s in skills):
            out["installed"].append({"name": name, "skills": skills, "last_modified_iso": last_mt})
        else:
            out["vendored_unused"].append(
                {"name": name, "cloned_at_iso": last_mt, "skills": skills}
            )
    return out
