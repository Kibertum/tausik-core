"""Host evidence is separate from installed hook configuration.

A profile scan cannot establish user trust or intercept arbitrary host writes.
This reader describes the last *reported live probe*, never a universal guarantee.
"""

from __future__ import annotations

import hashlib
import json
import string
from datetime import datetime, timezone
from pathlib import Path

from enforcement_coverage import SETTINGS_FILES, deployed_enforcement, profile_dir_for
from tausik_version import __version__ as VERSION

ROUTES = ("patch", "shell", "nested")
CASES = ("no_task", "out_of_scope", "allowed")


def profile_fingerprint(profile: Path) -> str:
    """Fingerprint installed enforcement inputs without exporting their contents."""
    digest = hashlib.sha256()
    for name in SETTINGS_FILES:
        path = profile / name
        digest.update(name.encode())
        try:
            digest.update(path.read_bytes())
        except FileNotFoundError:
            digest.update(b"absent")
    payloads = [
        *((profile / "plugins").glob("**/*")),
        *((profile / "scripts").glob("**/*.py")),
    ]
    for path in sorted(p for p in payloads if p.is_file() and not p.is_symlink()):
        digest.update(path.relative_to(profile).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in string.hexdigits for char in value)
    )


def _route_status(cases: dict) -> str:
    for name in CASES:
        row = cases.get(name)
        if not isinstance(row, dict) or row.get("result") != "completed":
            return "unknown"
        if not _is_sha256(row.get("before_sha256")) or not _is_sha256(row.get("after_sha256")):
            return "unknown"
        changed = row["before_sha256"] != row["after_sha256"]
        if name != "allowed":
            if changed:
                return "local_report_failed"
            if row.get("denied") is not True or row.get("hook_fired") is not True:
                return "unknown"
        elif row.get("denied") is not False or not changed:
            return "unknown"
    return "local_report_passed"


def live_enforcement_status(
    project_dir: str,
    host: str,
    *,
    host_version: str | None = None,
    now: datetime | None = None,
    max_age_seconds: int = 86400,
) -> dict:
    """Read local, version-bound probe evidence; stale/untrusted stays unknown.

    Installation and observation are different dimensions. Evidence is locally
    reported, not authenticated host attestation. Trust changes outside the
    profile are not observable here, so a historical probe is not current trust.
    """
    profile_name = profile_dir_for(project_dir, host)
    if profile_name is None:
        return {"host": host, "status": "unsupported", "routes": {}}
    profile = Path(profile_name)
    found = deployed_enforcement(str(profile))
    result = {
        "host": host,
        "installed": any(found.values()),
        "configuration": found,
        "host_version": host_version,
        "framework_version": VERSION,
        "status": "unknown",
        "attestation": "none",
        "proof": False,
        "hook_fired": None,
        "observed_at": None,
        "routes": {r: "unknown" for r in ROUTES},
        "limit": "reported historical probe; current host trust is not observable",
    }
    evidence_path = Path(project_dir) / ".tausik" / "enforcement" / (host + ".json")
    try:
        data = json.loads(evidence_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            return result
        observed_at = datetime.fromisoformat(data["observed_at"].replace("Z", "+00:00"))
        clock = now or datetime.now(timezone.utc)
        age = (clock - observed_at).total_seconds()
        result["observed_at"] = data["observed_at"]
        if (
            data.get("host") != host
            or data.get("mode") != "live_host"
            or data.get("framework_version") != VERSION
            or not data.get("host_version")
            or (host_version is not None and data["host_version"] != host_version)
            or data.get("profile_sha256") != profile_fingerprint(profile)
            or not 0 <= age <= max_age_seconds
        ):
            result["status"] = "stale_or_unmatched"
            return result
        result["host_version"] = data["host_version"]
        if data.get("trusted") is not True:
            result["status"] = "trust_unknown"
            return result
        routes = data.get("routes")
        if not isinstance(routes, dict):
            return result
        result_routes = {r: _route_status(routes.get(r, {})) for r in ROUTES}
        result["routes"] = result_routes
        result["hook_fired"] = any(
            isinstance(c, dict) and c.get("hook_fired") is True
            for cases in routes.values()
            if isinstance(cases, dict)
            for c in cases.values()
        )
        result["attestation"] = "local_self_reported"
        result["status"] = (
            "local_live_report"
            if all(value != "unknown" for value in result_routes.values())
            else "incomplete_local_report"
        )
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return result
    return result
