"""Brain status collector — mirror freshness, sync state, registry view.

Stack-agnostic, stdlib-only. Used by the `tausik brain status` CLI and the
matching `/brain status` skill action. All operations degrade gracefully:
missing mirror, unreadable config, or empty registry never raise.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

import brain_config
import brain_project_registry

CATEGORIES = ("decisions", "web_cache", "patterns", "gotchas")


def _utcnow_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safe_stat(path: str) -> tuple[int | None, str | None]:
    """Return (size_bytes, last_modified_iso) or (None, None) on missing/error."""
    try:
        st = os.stat(path)
    except OSError:
        return None, None
    last_mod = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()
    return st.st_size, last_mod.replace("+00:00", "Z")


def _per_category_state(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """Per-category row count + sync_state info."""
    out: dict[str, dict[str, Any]] = {}
    for cat in CATEGORIES:
        info: dict[str, Any] = {
            "row_count": None,
            "last_pull_at": None,
            "last_error": None,
            "last_error_at": None,
        }
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM brain_{cat}").fetchone()
            info["row_count"] = int(row[0]) if row else 0
        except sqlite3.Error:
            pass
        try:
            row = conn.execute(
                "SELECT last_pull_at, last_error, last_error_at "
                "FROM sync_state WHERE category=?",
                (cat,),
            ).fetchone()
            if row:
                info["last_pull_at"] = row[0]
                info["last_error"] = row[1]
                info["last_error_at"] = row[2]
        except sqlite3.Error:
            pass
        out[cat] = info
    return out


def _last_web_cache_write(conn: sqlite3.Connection) -> str | None:
    """Most recent fetched_at on brain_web_cache, ISO or None."""
    try:
        row = conn.execute("SELECT MAX(fetched_at) FROM brain_web_cache").fetchone()
        return row[0] if row and row[0] else None
    except sqlite3.Error:
        return None


def _registered_projects() -> list[dict[str, str]]:
    """List of {name, canonical, hash} entries; [] when registry missing."""
    try:
        entries = brain_project_registry.load_registry()
    except Exception:
        return []
    out: list[dict[str, str]] = []
    for e in entries:
        if not isinstance(e, dict) or not e.get("name"):
            continue
        out.append(
            {
                "name": str(e.get("name", "")),
                "canonical": str(e.get("canonical", "")),
                "hash": str(e.get("hash", "")),
            }
        )
    return out


def collect_status() -> dict[str, Any]:
    """Snapshot the brain subsystem.

    Never raises. Returns a dict with `enabled`, `mirror_path`,
    `mirror_size_bytes`, `mirror_last_modified`, `categories`, `projects`,
    `last_web_cache_write`, `error` (only when mirror is unreachable).
    Each per-category dict includes `row_count`, `last_pull_at`,
    `last_error`, `last_error_at`.
    """
    snapshot: dict[str, Any] = {
        "collected_at": _utcnow_iso(),
        "enabled": False,
        "mirror_path": None,
        "mirror_size_bytes": None,
        "mirror_last_modified": None,
        "categories": {},
        "projects": _registered_projects(),
        "last_web_cache_write": None,
        "error": None,
    }
    try:
        cfg = brain_config.load_brain()
    except Exception as e:
        snapshot["error"] = f"config unreadable: {e}"
        return snapshot
    snapshot["enabled"] = bool(cfg.get("enabled"))
    if not snapshot["enabled"]:
        return snapshot

    try:
        mirror_path = brain_config.get_brain_mirror_path()
    except Exception as e:
        snapshot["error"] = f"mirror_path unresolvable: {e}"
        return snapshot
    snapshot["mirror_path"] = mirror_path
    size, last_mod = _safe_stat(mirror_path)
    snapshot["mirror_size_bytes"] = size
    snapshot["mirror_last_modified"] = last_mod
    if size is None:
        snapshot["error"] = "mirror DB missing on disk"
        return snapshot

    try:
        conn = sqlite3.connect(mirror_path)
    except sqlite3.Error as e:
        snapshot["error"] = f"mirror unreadable: {e}"
        return snapshot
    try:
        snapshot["categories"] = _per_category_state(conn)
        snapshot["last_web_cache_write"] = _last_web_cache_write(conn)
    finally:
        conn.close()
    return snapshot


def format_status(snapshot: dict[str, Any]) -> str:
    """Render a `collect_status()` dict as human-readable markdown."""
    lines: list[str] = ["# Brain status"]
    lines.append(f"_collected at {snapshot.get('collected_at', '?')}_\n")
    lines.append(f"- enabled: **{snapshot.get('enabled')}**")
    if snapshot.get("error"):
        lines.append(f"- ⚠ error: {snapshot['error']}")
    if snapshot.get("mirror_path"):
        size = snapshot.get("mirror_size_bytes")
        size_str = f"{size:,} bytes" if isinstance(size, int) else "n/a"
        lines.append(f"- mirror: `{snapshot['mirror_path']}`")
        lines.append(f"- mirror size: {size_str}")
        lines.append(
            f"- mirror last modified: {snapshot.get('mirror_last_modified') or 'n/a'}"
        )
    last_wc = snapshot.get("last_web_cache_write")
    if last_wc:
        lines.append(f"- last web_cache write: {last_wc}")

    cats = snapshot.get("categories") or {}
    if cats:
        lines.append("\n## Categories")
        for cat in CATEGORIES:
            info = cats.get(cat) or {}
            rc = info.get("row_count")
            rc_str = str(rc) if rc is not None else "n/a"
            line = f"- **{cat}**: {rc_str} rows"
            if info.get("last_pull_at"):
                line += f" · last_pull_at={info['last_pull_at']}"
            if info.get("last_error"):
                line += f" · ⚠ last_error={info['last_error'][:60]}"
            lines.append(line)

    projects = snapshot.get("projects") or []
    if projects:
        lines.append("\n## Registered projects")
        for p in projects:
            lines.append(
                f"- {p.get('name', '?')} (canonical=`{p.get('canonical', '?')}`, "
                f"hash=`{p.get('hash', '?')[:16]}`)"
            )
    else:
        lines.append("\n_No projects registered yet._")

    return "\n".join(lines)
