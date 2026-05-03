"""r14-task-gate-secure — direct SQLite + fail_secure flag.

Replaces subprocess-based check with sqlite3 SELECT. Adds opt-in
TAUSIK_HOOK_FAIL_SECURE for environments where silent fail-open is
unacceptable.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys


_HOOK = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "scripts", "hooks", "task_gate.py"
    )
)


def _make_tausik_project(tmp_path, *, with_active_task: bool, broken_db: bool = False):
    """Construct a minimal TAUSIK project layout in tmp_path."""
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    db = tausik_dir / "tausik.db"
    if broken_db:
        # Write garbage to make sqlite3 throw.
        db.write_bytes(b"not a sqlite db")
    else:
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE tasks (slug TEXT PRIMARY KEY, status TEXT)"
        )
        if with_active_task:
            conn.execute("INSERT INTO tasks VALUES (?, ?)", ("t", "active"))
        else:
            conn.execute("INSERT INTO tasks VALUES (?, ?)", ("t", "planning"))
        conn.commit()
        conn.close()
    return tmp_path


def _run(env_extra: dict, cwd):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)}
    # Drop hostile parent env first, then apply test overrides — otherwise
    # a parent-set TAUSIK_SKIP_HOOKS would short-circuit every test, and a
    # parent-set TAUSIK_HOOK_FAIL_SECURE would invert the default-policy
    # tests. env_extra has the final say.
    for k in ("TAUSIK_SKIP_HOOKS", "TAUSIK_HOOK_FAIL_SECURE"):
        env.pop(k, None)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, _HOOK],
        input='{"tool_name":"Write","tool_input":{}}',
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


def test_active_task_allows(tmp_path):
    proj = _make_tausik_project(tmp_path, with_active_task=True)
    res = _run({}, proj)
    assert res.returncode == 0, res.stderr


def test_no_active_task_blocks(tmp_path):
    proj = _make_tausik_project(tmp_path, with_active_task=False)
    res = _run({}, proj)
    assert res.returncode == 2
    assert "BLOCKED" in res.stderr


def test_no_tausik_dir_allows(tmp_path):
    # No .tausik/ at all → not a tausik project, no enforcement.
    res = _run({}, tmp_path)
    assert res.returncode == 0


def test_fail_open_default_on_db_error(tmp_path):
    """Default: corrupt DB does NOT brick editing — fail-open."""
    proj = _make_tausik_project(tmp_path, with_active_task=False, broken_db=True)
    res = _run({}, proj)
    assert res.returncode == 0


def test_fail_secure_blocks_on_db_error(tmp_path):
    """TAUSIK_HOOK_FAIL_SECURE=1: corrupt DB → block."""
    proj = _make_tausik_project(tmp_path, with_active_task=False, broken_db=True)
    res = _run({"TAUSIK_HOOK_FAIL_SECURE": "1"}, proj)
    assert res.returncode == 2
    assert "FAIL_SECURE" in res.stderr


def test_skip_hooks_env_short_circuits(tmp_path):
    proj = _make_tausik_project(tmp_path, with_active_task=False)
    res = _run({"TAUSIK_SKIP_HOOKS": "1"}, proj)
    assert res.returncode == 0


def test_no_subprocess_left_in_hook_source():
    """Static check: the hook must no longer rely on `subprocess.run`.

    Catches a regression that would re-introduce the 5s timeout flake
    and kill editor responsiveness on Windows.
    """
    with open(_HOOK, encoding="utf-8") as f:
        src = f.read()
    assert "subprocess.run" not in src, (
        "task_gate.py must use direct sqlite3 SELECT, not subprocess"
    )
