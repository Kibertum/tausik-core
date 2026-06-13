"""TAUSIK CLI handler for `tausik renar` (v16r-conformance-yaml).

`tausik renar conformance` generates a RENAR-CONFORMANCE.yaml self-assessment
whose level is computed from live DB state (§14.4.3), not declared. Prints to
stdout; `--write` persists to RENAR-CONFORMANCE.yaml at the project root.
"""

from __future__ import annotations

import os
from typing import Any

import yaml

from project_service import ProjectService
from renar_conformance import generate
from tausik_utils import utcnow_iso


def _existing_version(path: str) -> int:
    """Read manifest-version from an existing manifest; 0 if absent/unreadable."""
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return int(data.get("manifest-version", 0))
    except (OSError, ValueError, yaml.YAMLError):
        return 0


def cmd_renar(svc: ProjectService, args: Any) -> None:
    cmd = getattr(args, "renar_cmd", None) or "conformance"
    if cmd != "conformance":
        print(f"Unknown renar subcommand: {cmd!r}")
        return
    assessor = getattr(args, "assessor", None) or "architect-andrey-y"
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
