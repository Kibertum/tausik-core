"""Sibling-MCP reporting helpers — report-only, never kills (decision #189).

The recurring "MCP feels hung / drifts" class (#77/#79/#80) is driven by
sibling tausik-project MCP servers accumulating: each Claude Code session in a
window spawns its own server.py, and old ones live as long as their owning
claude.exe does. The 2026-07-18 forensics (Win11 build 26200) found no ORPHANS
— every sibling sat under a LIVE claude.exe in the same Code.exe window, so a
stale-but-alive session is indistinguishable from an active one by the process
tree. Auto-reaping would therefore risk killing a live session (its WAL
connection and in-flight work). The safe contract is to REPORT and warn, not
kill — which makes "live siblings are never killed" true by construction, with
no killer code to misfire.

The real latency pain was not the absence of reaping: `_enumerate_sibling_mcps`
spawned a fresh PowerShell `Get-CimInstance` on EVERY self_check call (wmic was
removed from the Win11 26200 base image, so the wmic path always fell through),
~0.6-1s over 100+ processes, which made `/start` look like a hang.
`cached_enumerate` memoizes the result behind a short TTL so repeated checks in
a session reuse it instead of re-probing.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

# What `cached_enumerate` memoizes, so the caller's type survives the round trip
# instead of being flattened to Any at the cache boundary.
_Enumerated = TypeVar("_Enumerated")

# Above this many sibling MCP servers for ONE project, escalate from an
# informational count to a hard warning: it signals accumulated Claude Code
# sessions the operator should close. A small number is normal (one or two
# concurrent sessions), so the threshold sits just above routine use.
SIBLING_WARN_THRESHOLD = 3

# Seconds a sibling enumeration stays fresh. A diagnostic can tolerate this much
# staleness; the sibling set changes on the scale of opening/closing sessions,
# not sub-second. Kept here (not in self_check) so it is testable in isolation.
SIBLING_ENUM_TTL_SECONDS = 30.0


def sibling_warning(count: Any, *, threshold: int = SIBLING_WARN_THRESHOLD) -> str:
    """Hard-warning string when the sibling MCP `count` exceeds `threshold`.

    Returns "" for a normal count, for an unknown count (``-1``, introspection
    failed — the caller renders that state), and for a non-int. The message is
    deliberately advisory: it names the accumulation and points at closing old
    sessions, and it never claims the framework killed anything (decision #189).
    """
    if not isinstance(count, int) or isinstance(count, bool):
        return ""
    if count <= threshold:
        return ""
    return (
        f"WARNING: {count} sibling tausik-project MCP servers are alive for this "
        f"project (threshold {threshold}). This is accumulated Claude Code "
        f"sessions in one window, each holding a WAL connection to the same DB "
        f"and the likely cause of MCP feeling slow or drifting. Close old Claude "
        f"Code sessions/windows to release them — the framework will not kill a "
        f"process, since a live sibling session cannot be told apart from a "
        f"stale one by the process tree."
    )


def cached_enumerate(
    key: str,
    enum_fn: Callable[[], _Enumerated],
    *,
    ttl: float,
    now: float,
    cache: dict[str, tuple[float, _Enumerated]],
) -> _Enumerated:
    """Return a memoized enumeration for `key`, refreshing only after `ttl`.

    `cache` is a caller-owned dict of ``{key: (timestamp, value)}`` and `now` is
    a caller-supplied clock (e.g. ``time.monotonic()``) — both injected so the
    TTL logic is a pure, testable function with no hidden global state. Within
    the window the cached value is returned WITHOUT calling `enum_fn`, which is
    the whole point: no fresh PowerShell probe per self_check call (AC3).
    """
    entry = cache.get(key)
    if entry is not None:
        ts, value = entry
        if now - ts < ttl:
            return value
    value = enum_fn()
    cache[key] = (now, value)
    return value
