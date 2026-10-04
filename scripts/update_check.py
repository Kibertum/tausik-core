"""Check GitHub for a newer TAUSIK release without leaking project identity.

Until 1.10 nothing told a consumer that a release came out: a project on 1.8
learned about 1.9 by visiting github.com (owner, session #264, decision #372).

WHAT GOES OUT. One anonymous HTTPS GET to
``https://api.github.com/repos/Kibertum/tausik-core/releases/latest`` with a
fixed User-Agent. No project name, path, schema version, user or TAUSIK version
travels — the test intercepts the request and checks it. Measured on
2026-09-23: the REST call answered in ~1.1 s, `git ls-remote --tags` in ~1.4 s,
so the session-start check has a strict two-second timeout.

HOW. Every public session-start boundary performs a fresh check before opening
the session. A successful answer newer than the installed version refuses the
start and names the upgrade command. The separate `tausik update-check` command
retains its daily cache policy for status/doctor use.

WHAT FAILS HOW. No network, timeout, a GitHub error or a garbage answer records
the error and KEEPS the last good answer. Session start continues, but reports
the installed version as unverified; a failed check never means "up to date".

OFF. ``"updates": {"check": false}`` in .tausik/config.json. On by default: the
owner made the check mandatory in 1.10, and README says what leaves the machine.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

URL = "https://api.github.com/repos/Kibertum/tausik-core/releases/latest"
USER_AGENT = "tausik-update-check"
TIMEOUT_S = 5.0
SESSION_START_TIMEOUT_S = 2.0
INTERVAL = timedelta(hours=24)
CACHE_NAME = "update_check.json"


def enabled(cfg: dict[str, Any] | None) -> bool:
    return bool(((cfg or {}).get("updates") or {}).get("check", True))


def cache_path(tausik_dir: str) -> str:
    return os.path.join(tausik_dir, CACHE_NAME)


def read_cache(tausik_dir: str) -> dict[str, Any]:
    try:
        with open(cache_path(tausik_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_cache(tausik_dir: str, data: dict[str, Any]) -> None:
    path = cache_path(tausik_dir)
    fd, tmp = tempfile.mkstemp(prefix=f".{CACHE_NAME}.", suffix=".tmp", dir=tausik_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _parse_version(tag: str) -> tuple[tuple[int, int, int], tuple[str, ...] | None] | None:
    """Parse SemVer without adding a runtime dependency; build metadata does not order."""
    match = re.fullmatch(
        r"v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
        r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
        str(tag).strip(),
    )
    if not match:
        return None
    core_parts = match.groups()[:3]
    if any(len(part) > 1 and part.startswith("0") for part in core_parts):
        return None
    core = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    prerelease = tuple(match.group(4).split(".")) if match.group(4) else None
    if prerelease and any(
        part.isdigit() and len(part) > 1 and part.startswith("0") for part in prerelease
    ):
        return None
    return core, prerelease


def compare_versions(left: str, right: str) -> int | None:
    """Return -1/0/1 under SemVer precedence, or None when either side is unknown."""
    one, two = _parse_version(left), _parse_version(right)
    if one is None or two is None:
        return None
    if one[0] != two[0]:
        return -1 if one[0] < two[0] else 1
    if one[1] is None or two[1] is None:
        if one[1] is two[1]:
            return 0
        return 1 if one[1] is None else -1
    for left_part, right_part in zip(one[1], two[1], strict=False):
        if left_part == right_part:
            continue
        left_numeric, right_numeric = left_part.isdigit(), right_part.isdigit()
        if left_numeric and right_numeric:
            return -1 if int(left_part) < int(right_part) else 1
        if left_numeric != right_numeric:
            return -1 if left_numeric else 1
        return -1 if left_part < right_part else 1
    return (len(one[1]) > len(two[1])) - (len(one[1]) < len(two[1]))


def build_request() -> urllib.request.Request:
    """The one request that leaves the machine. Nothing project-specific in it."""
    return urllib.request.Request(
        URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
        method="GET",
    )


def fetch_latest(
    opener: Callable[..., Any] = urllib.request.urlopen, timeout: float = TIMEOUT_S
) -> dict[str, str]:
    """Ask GitHub; raise ValueError on an answer that is not a release."""
    with opener(build_request(), timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    tag = str(payload.get("tag_name") or "")
    if _parse_version(tag) is None:
        raise ValueError(f"not a release tag: {tag!r}")
    return {"latest": tag.lstrip("v"), "url": str(payload.get("html_url") or "")}


def due(cache: dict[str, Any], now: datetime) -> bool:
    try:
        last = datetime.fromisoformat(str(cache["checked_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return True
    return now - last >= INTERVAL


def refresh(
    tausik_dir: str,
    now: datetime | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
    force: bool = False,
    timeout: float = TIMEOUT_S,
) -> dict[str, Any]:
    """Fetch when due and record the answer; keep the last good one on failure."""
    now = now or datetime.now(timezone.utc)
    cache = read_cache(tausik_dir)
    if not force and not due(cache, now):
        return cache
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        answer = fetch_latest(opener, timeout=timeout)
        cache = {**answer, "checked_at": stamp, "ok_at": stamp}
    except Exception as e:  # noqa: BLE001 — any failure is recorded, none is fatal
        cache = {
            **{k: cache[k] for k in ("latest", "url", "ok_at") if k in cache},
            "checked_at": stamp,
            "error": f"{type(e).__name__}: {e}"[:200],
        }
    try:
        _write_cache(tausik_dir, cache)
    except OSError as e:
        cache["cache_warning"] = f"cache persistence failed ({type(e).__name__}: {e})"[:200]
    return cache


def notice(cache: dict[str, Any], current: str) -> str | None:
    """One line when the cached answer is newer than what runs; None otherwise."""
    order = compare_versions(str(cache.get("latest", "")), current)
    if order is None or order <= 0:
        return None
    url = cache.get("url") or "https://github.com/Kibertum/tausik-core/releases"
    return f"TAUSIK {cache['latest']} is available (this project runs {current}): {url}"


def session_start_release_check(
    svc: Any,
    *,
    now: datetime | None = None,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Perform the release check for a public session-start boundary.

    Only an authoritative successful answer can block. Privacy opt-out and
    failures stay explicit as disabled/unknown and never masquerade as current.
    """
    from project_config import load_config
    from tausik_utils import ServiceError
    from tausik_version import __version__

    tausik_dir = svc.tausik_dir()
    if os.path.basename(os.path.normpath(tausik_dir)) != ".tausik":
        return {"status": "not-installed-layout", "fresh": False}
    cfg = load_config(tausik_dir)
    if not enabled(cfg):
        return {
            "status": "disabled",
            "fresh": False,
            "warning": "release check disabled by updates.check=false; installed version is unverified",
        }
    cache = refresh(
        tausik_dir,
        now=now,
        opener=opener or urllib.request.urlopen,
        force=True,
        timeout=SESSION_START_TIMEOUT_S,
    )
    if cache.get("error"):
        persistence = f"; {cache['cache_warning']}" if cache.get("cache_warning") else ""
        return {
            "status": "unknown",
            "fresh": False,
            "warning": (
                f"release check failed; installed version is unverified "
                f"({cache['error']}){persistence}"
            ),
        }
    latest = str(cache.get("latest") or "")
    order = compare_versions(latest, __version__)
    if order is None:
        return {
            "status": "unknown",
            "fresh": False,
            "warning": "release check returned an unorderable version; installed version is unverified",
        }
    if order > 0:
        upgrade = (
            f"git -C .tausik-lib fetch --tags && git -C .tausik-lib checkout v{latest} "
            "&& python .tausik-lib/bootstrap/bootstrap.py --ide all"
        )
        raise ServiceError(
            f"TAUSIK session start refused: installed {__version__}, latest {latest}. "
            f"Upgrade: {upgrade}"
        )
    result = {
        "status": "checked",
        "fresh": True,
        "installed": __version__,
        "latest": latest,
        "checked_at": cache.get("checked_at"),
    }
    if cache.get("cache_warning"):
        result["warning"] = str(cache["cache_warning"])
    return result


def checked_session_start(svc: Any) -> str:
    """Run the shared direct-start path used by CLI and MCP transports."""
    check = session_start_release_check(svc)
    result = svc.session_start()
    warning = check.get("warning")
    return f"WARNING: {warning}\n{result}" if warning else result


def doctor_line(cfg: dict[str, Any] | None, cache: dict[str, Any]) -> tuple[str, str]:
    """(level, text) for `tausik doctor`: on/off, last checked, last answer."""
    if not enabled(cfg):
        return "ok", "off (updates.check = false)"
    if not cache:
        return "warn", "on, never checked yet"
    answer = f"latest {cache['latest']}" if cache.get("latest") else "no answer yet"
    if cache.get("error"):
        return (
            "warn",
            f"on, last check {cache.get('checked_at')} FAILED ({cache['error']}); {answer}",
        )
    return "ok", f"on, last checked {cache.get('checked_at')}; {answer}"


def cmd_update_check(svc: Any, args: Any) -> None:
    """`tausik update-check [--now]` — refresh the cache (when due) and print the state.

    SessionStart runs it detached; a person runs it to see the answer now.
    """
    from project_config import load_config
    from tausik_version import __version__

    td = svc.tausik_dir()
    cfg = load_config(td)
    if not enabled(cfg):
        print("update check: off (updates.check = false)")
        return
    cache = refresh(td, force=bool(getattr(args, "now", False)))
    print(doctor_line(cfg, cache)[1])
    line = notice(cache, __version__)
    print(line or f"TAUSIK {__version__} — no newer release known")
