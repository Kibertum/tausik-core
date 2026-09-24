"""Does a newer TAUSIK exist? Asked of GitHub, at most once a day, never blocking.

Until 1.10 nothing told a consumer that a release came out: a project on 1.8
learned about 1.9 by visiting github.com (owner, session #264, decision #372).

WHAT GOES OUT. One anonymous HTTPS GET to
``https://api.github.com/repos/Kibertum/tausik-core/releases/latest`` with a
fixed User-Agent. No project name, path, schema version, user or TAUSIK version
travels — the test intercepts the request and checks it. Measured on
2026-09-23: the REST call answered in ~1.1 s, `git ls-remote --tags` in ~1.4 s,
so neither may sit on the SessionStart path, whose hooks already run close to
their timeout (memory #708).

HOW. SessionStart spawns `tausik update-check` DETACHED; the refresh writes
``.tausik/update_check.json``. `tausik status` reads that cache and prints one
line when a newer release exists. So a release is seen no later than the start
of the session after the one that fetched it, and no session waits on the
network.

WHAT FAILS HOW. No network, a GitHub error or a garbage answer records the
error and KEEPS the last good answer — the cache is not poisoned, and "up to
date" is never claimed from a failed check. `tausik doctor` shows the state.

OFF. ``"updates": {"check": false}`` in .tausik/config.json. On by default: the
owner made the check mandatory in 1.10, and README says what leaves the machine.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

URL = "https://api.github.com/repos/Kibertum/tausik-core/releases/latest"
USER_AGENT = "tausik-update-check"
TIMEOUT_S = 5.0
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
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _parse_version(tag: str) -> tuple[int, ...] | None:
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(tag).strip())
    return tuple(int(x) for x in m.groups()) if m else None


def build_request() -> urllib.request.Request:
    """The one request that leaves the machine. Nothing project-specific in it."""
    return urllib.request.Request(
        URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
        method="GET",
    )


def fetch_latest(opener: Callable[..., Any] = urllib.request.urlopen) -> dict[str, str]:
    """Ask GitHub; raise ValueError on an answer that is not a release."""
    with opener(build_request(), timeout=TIMEOUT_S) as resp:
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
) -> dict[str, Any]:
    """Fetch when due and record the answer; keep the last good one on failure."""
    now = now or datetime.now(timezone.utc)
    cache = read_cache(tausik_dir)
    if not force and not due(cache, now):
        return cache
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        answer = fetch_latest(opener)
        cache = {**answer, "checked_at": stamp, "ok_at": stamp}
    except Exception as e:  # noqa: BLE001 — any failure is recorded, none is fatal
        cache = {
            **{k: cache[k] for k in ("latest", "url", "ok_at") if k in cache},
            "checked_at": stamp,
            "error": f"{type(e).__name__}: {e}"[:200],
        }
    _write_cache(tausik_dir, cache)
    return cache


def notice(cache: dict[str, Any], current: str) -> str | None:
    """One line when the cached answer is newer than what runs; None otherwise."""
    latest, cur = _parse_version(cache.get("latest", "")), _parse_version(current)
    if latest is None or cur is None or latest <= cur:
        return None
    url = cache.get("url") or "https://github.com/Kibertum/tausik-core/releases"
    return f"TAUSIK {cache['latest']} is available (this project runs {current}): {url}"


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
