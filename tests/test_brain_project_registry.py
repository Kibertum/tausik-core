"""Tests for scripts/brain_project_registry.py."""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_project_registry as bpr  # noqa: E402


@pytest.fixture
def reg_path(tmp_path, monkeypatch):
    """Point the registry at a temp file isolated from the host machine."""
    p = tmp_path / "projects.json"
    monkeypatch.setenv("TAUSIK_BRAIN_REGISTRY", str(p))
    return p


def test_get_registry_path_uses_env_override(reg_path):
    assert bpr.get_registry_path() == os.path.abspath(str(reg_path))


def test_get_registry_path_default(monkeypatch, tmp_path):
    monkeypatch.delenv("TAUSIK_BRAIN_REGISTRY", raising=False)
    p = bpr.get_registry_path()
    assert p.endswith(os.path.join(".tausik-brain", "projects.json"))
    assert os.path.isabs(p)


def test_canonical_name_normalization():
    assert bpr.canonical_name("Hello World") == "hello-world"
    assert bpr.canonical_name("  myapp  ") == "myapp"
    assert bpr.canonical_name("MixedCase") == "mixedcase"
    assert bpr.canonical_name("multi  space  name") == "multi-space-name"


def test_canonical_name_empty_raises():
    with pytest.raises(ValueError):
        bpr.canonical_name("   ")
    with pytest.raises(ValueError):
        bpr.canonical_name("")


def test_canonical_name_non_string_raises():
    with pytest.raises(TypeError):
        bpr.canonical_name(None)  # type: ignore[arg-type]


def test_load_registry_missing_returns_empty(reg_path):
    assert bpr.load_registry() == []


def test_load_registry_malformed_returns_empty(reg_path):
    reg_path.write_text("{not json", encoding="utf-8")
    assert bpr.load_registry() == []


def test_load_registry_non_list_returns_empty(reg_path):
    reg_path.write_text('{"not": "a list"}', encoding="utf-8")
    assert bpr.load_registry() == []


def test_load_registry_filters_bad_entries(reg_path):
    reg_path.write_text(
        json.dumps([{"name": "ok"}, "string", 42, {"missing_name": True}]),
        encoding="utf-8",
    )
    assert bpr.load_registry() == [{"name": "ok"}]


def test_save_load_round_trip(reg_path):
    entries = [{"name": "foo", "path": "/x", "hash": "deadbeef"}]
    bpr.save_registry(entries)
    assert bpr.load_registry() == entries


def test_save_is_atomic_creates_parent_dirs(tmp_path, monkeypatch):
    nested = tmp_path / "deep" / "nested" / "reg.json"
    monkeypatch.setenv("TAUSIK_BRAIN_REGISTRY", str(nested))
    bpr.save_registry([{"name": "foo"}])
    assert nested.exists()
    # Temp file must not linger.
    assert not (nested.parent / "reg.json.tmp").exists()


def test_register_project_new_entry(reg_path):
    entry = bpr.register_project("FooBar", "/projects/foobar")
    assert entry["name"] == "foobar"
    assert entry["canonical"] == "foobar"
    assert len(entry["hash"]) == 16
    assert entry["registered_at"].endswith("Z")
    # Persisted.
    loaded = bpr.load_registry()
    assert len(loaded) == 1
    assert loaded[0]["canonical"] == "foobar"


def test_register_project_idempotent_same_path(reg_path):
    bpr.register_project("FooBar", "/projects/foobar", now="2026-01-01T00:00:00Z")
    second = bpr.register_project("FooBar", "/projects/foobar")
    # second call returns the first entry unchanged, does NOT create a new row
    assert second["registered_at"] == "2026-01-01T00:00:00Z"
    assert len(bpr.load_registry()) == 1


def test_register_project_collision_auto_increments(reg_path):
    """Two different paths, same canonical name → name, name-2, name-3."""
    a = bpr.register_project("foobar", "/projects/a")
    b = bpr.register_project("foobar", "/projects/b")
    c = bpr.register_project("foobar", "/projects/c")
    assert a["name"] == "foobar"
    assert b["name"] == "foobar-2"
    assert c["name"] == "foobar-3"
    assert len(bpr.load_registry()) == 3


def test_register_project_collision_with_canonical_input(reg_path):
    """Input variants ('FooBar' vs 'foobar') collide on canonical form."""
    bpr.register_project("foobar", "/a")
    b = bpr.register_project("FooBar", "/b")
    assert b["canonical"] == "foobar-2"


def test_register_project_normalizes_paths(reg_path):
    """Same path via different forms (rel vs abs, double slash) must dedupe."""
    cwd = os.getcwd()
    e1 = bpr.register_project("foo", cwd)
    e2 = bpr.register_project("foo", cwd + os.sep)
    assert e1 == e2
    assert len(bpr.load_registry()) == 1


def test_register_project_empty_path_raises(reg_path):
    with pytest.raises(ValueError):
        bpr.register_project("foo", "")


def test_all_project_names_union(reg_path):
    bpr.register_project("foo", "/a")
    bpr.register_project("bar", "/b")
    bpr.register_project("foo", "/c")  # collision → foo-2
    names = bpr.all_project_names()
    assert set(names) == {"foo", "bar", "foo-2"}


def test_all_project_names_empty(reg_path):
    assert bpr.all_project_names() == []


def test_save_unlinks_tmp_on_failure(reg_path, monkeypatch):
    """If json.dump raises, the .tmp file must not linger on disk."""
    import json as _json

    def boom(*_a, **_k):
        raise RuntimeError("simulated disk failure")

    monkeypatch.setattr(_json, "dump", boom)
    with pytest.raises(RuntimeError):
        bpr.save_registry([{"name": "x"}])
    assert not os.path.exists(str(reg_path) + ".tmp")
    assert not reg_path.exists()


def test_register_lock_prevents_concurrent_write(reg_path):
    """Holding the lockfile blocks a second register_project until timeout."""
    lock_path = bpr._acquire_lock(str(reg_path), timeout_s=0.1)
    try:
        with pytest.raises(bpr.RegistryLockError):
            bpr.register_project("foo", "/a")
    finally:
        bpr._release_lock(lock_path)
    # lock released → subsequent call succeeds
    entry = bpr.register_project("foo", "/a")
    assert entry["name"] == "foo"


# --- Stale-lock recovery (brain-registry-stale-lock-recovery) -----------


def _unused_pid() -> int:
    """Return a PID `_pid_alive` reports as dead — PID 0 hits the early
    `pid <= 0` return without an OS-level kill call.

    Walking the PID space via `os.kill(pid, 0)` was unreliable on Windows
    GitHub runners (many system PIDs raise PermissionError, treated as
    alive). Spawning a subprocess and reaping it also hung on Windows CI.
    PID 0 exercises the same lock-reclamation pipeline (stored PID treated
    as dead → lock reclaimed) without depending on OS PID semantics.
    """
    return 0


def test_dead_pid_lock_is_reclaimed(reg_path):
    """Lock with a dead PID is treated as stale → reclaimed on next acquire."""
    lock_path = str(reg_path) + ".lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w") as f:
        f.write(str(_unused_pid()))
    entry = bpr.register_project("foo", "/a")
    assert entry["name"] == "foo"


def test_expired_mtime_lock_is_reclaimed(reg_path):
    """Lock with a live PID but old mtime is still reclaimed."""
    import time as _time

    lock_path = str(reg_path) + ".lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))  # live pid — would normally block
    # Backdate mtime beyond the stale threshold
    old = _time.time() - (bpr._STALE_LOCK_AGE_S + 10)
    os.utime(lock_path, (old, old))
    entry = bpr.register_project("bar", "/b")
    assert entry["name"] == "bar"


def test_live_fresh_lock_not_reclaimed(reg_path):
    """Regression: lock with live PID + recent mtime still blocks."""
    lock_path = bpr._acquire_lock(str(reg_path), timeout_s=0.1)
    try:
        with pytest.raises(bpr.RegistryLockError):
            bpr.register_project("foo", "/a", path=str(reg_path))
    finally:
        bpr._release_lock(lock_path)


def test_malformed_lock_reclaimed_after_ttl(reg_path):
    """Lock with non-integer content is stale once mtime exceeds the threshold."""
    import time as _time

    lock_path = str(reg_path) + ".lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w") as f:
        f.write("not-a-pid-at-all")
    old = _time.time() - (bpr._STALE_LOCK_AGE_S + 5)
    os.utime(lock_path, (old, old))
    entry = bpr.register_project("foo", "/a")
    assert entry["name"] == "foo"


def test_malformed_lock_not_yet_stale_blocks(reg_path):
    """Boundary: malformed lock with fresh mtime still blocks (no PID to verify)."""
    lock_path = str(reg_path) + ".lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w") as f:
        f.write("junk")
    with pytest.raises(bpr.RegistryLockError):
        bpr._acquire_lock(str(reg_path), timeout_s=0.1)
    # Cleanup so other tests don't inherit a blocked lock
    os.unlink(lock_path)


def test_is_stale_lock_missing_file_returns_false(tmp_path):
    """No file to inspect → not stale (caller will create fresh on next try)."""
    assert bpr._is_stale_lock(str(tmp_path / "missing.lock")) is False


def test_pid_alive_rejects_nonpositive():
    assert bpr._pid_alive(0) is False
    assert bpr._pid_alive(-1) is False


def test_explicit_canonical_collides_with_auto_suffix(reg_path):
    """Pin current behavior: explicit `foobar-2` input after the auto suffix exists.

    Currently yields `foobar-2-2`. Intentional — any variant shape is
    still in the union-blocklist, so scrubbing safety is unaffected.
    """
    bpr.register_project("foobar", "/a")
    bpr.register_project("foobar", "/b")  # → foobar-2
    entry = bpr.register_project("foobar-2", "/c")  # collides with auto suffix
    assert entry["name"] == "foobar-2-2"
