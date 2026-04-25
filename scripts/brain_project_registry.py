"""Global registry of TAUSIK-enabled projects: ~/.tausik-brain/projects.json.

Two concerns, one file:
  1. Assign a unique canonical name for each project on the machine. If two
     projects resolve to the same canonical name ("princess" vs. another
     "princess"), auto-increment: "princess", "princess-2", ...
  2. Expose all registered project names so the scrubbing linter can build
     a union-blocklist across projects (so project A does not accidentally
     leak project B's name into brain).

Storage: plain JSON list of entries, each:
  {"name": str, "path": str, "registered_at": ISO-UTC, "canonical": str,
   "hash": 16-hex}

Zero external deps. Atomic writes with .tmp unlink on failure. Path override
via env TAUSIK_BRAIN_REGISTRY for tests and custom layouts.

**Concurrency model: single writer.** Running `tausik brain init` in two
processes against the same registry simultaneously is undefined — v1 assumes
a developer only runs one wizard at a time. A coarse advisory lock is
provided by `_with_lock`, but it is best-effort; on contention the second
wizard raises `RegistryLockError`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone

import brain_config

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH = os.path.join("~", ".tausik-brain", "projects.json")
_ENV_OVERRIDE = "TAUSIK_BRAIN_REGISTRY"


def get_registry_path() -> str:
    """Absolute path to projects.json, honoring the TAUSIK_BRAIN_REGISTRY env var."""
    raw = os.environ.get(_ENV_OVERRIDE) or DEFAULT_REGISTRY_PATH
    return os.path.abspath(os.path.expandvars(os.path.expanduser(raw)))


def canonical_name(name: str) -> str:
    """Normalize a project name: strip, lower, collapse whitespace to '-'."""
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    stripped = name.strip()
    if not stripped:
        raise ValueError("name must be non-empty")
    return re.sub(r"\s+", "-", stripped.lower())


def _normalize_path(path: str) -> str:
    """Filesystem-safe path comparator: absolute + normcase (handles Win slash/case)."""
    return os.path.normcase(os.path.abspath(path))


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_registry(path: str | None = None) -> list[dict]:
    """Read projects.json. Returns [] if missing or corrupt.

    Corrupt JSON is treated as empty (recoverable on next save). OSError
    (permission/IO) is logged and also returns [] so the wizard remains
    usable even on a temporarily unreadable registry — caller should expect
    overwrite-on-save in that case.
    """
    p = path or get_registry_path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.warning("Registry at %s is corrupt JSON; treating as empty", p)
        return []
    except OSError as e:
        logger.warning("Registry at %s unreadable (%s); treating as empty", p, e)
        return []
    if not isinstance(data, list):
        return []
    return [e for e in data if isinstance(e, dict) and e.get("name")]


def save_registry(entries: list[dict], path: str | None = None) -> None:
    """Atomic write: temp file + fsync + os.replace, unlink .tmp on failure."""
    p = path or get_registry_path()
    parent = os.path.dirname(p)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = p + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# --- Advisory lock --------------------------------------------------------


class RegistryLockError(RuntimeError):
    """Raised when a concurrent wizard holds the registry lock."""


_STALE_LOCK_AGE_S = 30.0


def _pid_alive(pid: int) -> bool:
    """True iff the process with this PID exists. OS-agnostic via os.kill(pid, 0)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Exists but we can't signal — still alive from our point of view.
        return True
    except OSError:
        # Windows returns ERROR_INVALID_PARAMETER for non-existent PIDs.
        return False
    return True


def _is_stale_lock(lock_path: str) -> bool:
    """Lock is stale if (a) pid inside does not exist, or (b) mtime older than threshold.

    Malformed / empty lock: fall back to mtime check. Read errors → False
    (conservative — keep blocking rather than racing on unreadable state).
    """
    try:
        mtime = os.path.getmtime(lock_path)
    except OSError:
        return False
    try:
        with open(lock_path, encoding="utf-8") as f:
            raw = f.read().strip()
    except OSError as e:
        logger.warning("Lock %s unreadable (%s); treating as not stale", lock_path, e)
        return False
    age = time.time() - mtime
    try:
        pid = int(raw)
    except ValueError:
        return age > _STALE_LOCK_AGE_S
    if not _pid_alive(pid):
        return True
    return age > _STALE_LOCK_AGE_S


def _acquire_lock(path: str, *, timeout_s: float = 2.0) -> str:
    """Create a sibling .lock via O_EXCL. Returns lock path; raises on timeout.

    Recovers from stale locks left by SIGKILLed wizards: if the existing lock's
    PID is dead (or its mtime exceeds `_STALE_LOCK_AGE_S`), delete it and retry.

    Contract: at most ONE stale-lock reclaim per call (`reclaimed` flag). After
    one reclaim+retry, subsequent FileExistsError contention waits out the
    `timeout_s` and raises `RegistryLockError`. This prevents an adversarial
    loop where a third process keeps recreating the lock between our
    `_is_stale_lock` and `os.unlink` (a small TOCTOU window: their fresh lock
    looks live to the next caller's `_is_stale_lock` check, so the next call
    will wait normally rather than incorrectly reclaim a live lock).
    """
    lock_path = path + ".lock"
    deadline = time.monotonic() + timeout_s
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    reclaimed = False
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return lock_path
        except FileExistsError:
            if not reclaimed and _is_stale_lock(lock_path):
                try:
                    os.unlink(lock_path)
                    logger.warning("Reclaimed stale registry lock at %s", lock_path)
                except OSError:
                    pass
                reclaimed = True
                continue
            if time.monotonic() >= deadline:
                raise RegistryLockError(
                    f"Registry is locked by another process (see {lock_path!r})"
                ) from None
            time.sleep(0.05)


def _release_lock(lock_path: str) -> None:
    try:
        os.unlink(lock_path)
    except OSError:
        pass


def _find_by_path(entries: list[dict], norm_path: str) -> dict | None:
    for e in entries:
        if _normalize_path(e.get("path", "")) == norm_path:
            return e
    return None


def _pick_unique_canonical(entries: list[dict], base_canonical: str) -> str:
    taken = {
        e.get("canonical") or canonical_name(e.get("name", ""))
        for e in entries
        if e.get("name")
    }
    if base_canonical not in taken:
        return base_canonical
    i = 2
    while f"{base_canonical}-{i}" in taken:
        i += 1
    return f"{base_canonical}-{i}"


def register_project(
    name: str,
    project_path: str,
    *,
    path: str | None = None,
    now: str | None = None,
) -> dict:
    """Register (or re-resolve) a project entry.

    Behavior:
      - If an entry with the same normalized project_path already exists,
        returns it unchanged (idempotent re-register).
      - Otherwise canonicalizes `name`, auto-increments on collision with
        a different path, appends entry + saves atomically. Returns the new entry.

    Returns the entry dict with {name, path, canonical, hash, registered_at}.
    """
    if not project_path or not isinstance(project_path, str):
        raise ValueError("project_path is required")
    base_canonical = canonical_name(name)
    norm_path = _normalize_path(project_path)

    reg_path = path or get_registry_path()
    lock = _acquire_lock(reg_path)
    try:
        entries = load_registry(path)
        existing = _find_by_path(entries, norm_path)
        if existing:
            return existing

        unique = _pick_unique_canonical(entries, base_canonical)
        entry = {
            "name": unique,
            "path": norm_path,
            "canonical": unique,
            "hash": brain_config.compute_project_hash(unique),
            "registered_at": now or _now_iso(),
        }
        entries.append(entry)
        save_registry(entries, path)
        return entry
    finally:
        _release_lock(lock)


def all_project_names(path: str | None = None) -> list[str]:
    """Union of `name` fields across all registered projects — feeds scrubbing blocklist."""
    return [e["name"] for e in load_registry(path) if e.get("name")]
