"""The bootstrap chain's third link: a running process versus the tree it runs from.

`bootstrap-drift-gate-off-source-edits-never-reach-the-cli`. The first link
(the gate stood OFF) was closed by decision #287; what remained, measured in
session #191, was a live MCP server closing tasks with the gate set it had
imported before a redeploy. These tests drive the snapshot module and the
gate's use of it on synthetic trees under tmp_path — never against the real
`.claude/` profile, which is gitignored and absent on a fresh clone.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import running_source_drift as RSD  # noqa: E402

SERVER = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project", "server.py"
    )
)


def _tree(root, files: dict[str, str]) -> None:
    for name, body in files.items():
        path = root.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


class TestSnapshot:
    def test_unchanged_tree_reports_nothing(self, tmp_path):
        _tree(tmp_path, {"a.py": "x = 1\n", "sub/b.py": "y = 2\n"})
        snap = RSD.Snapshot([str(tmp_path)])
        assert snap.changed() == []

    def test_a_changed_file_is_named_with_its_root(self, tmp_path):
        _tree(tmp_path, {"a.py": "x = 1\n", "sub/b.py": "y = 2\n"})
        snap = RSD.Snapshot([str(tmp_path)])
        _tree(tmp_path, {"sub/b.py": "y = 3\n"})
        assert snap.changed() == [f"{tmp_path.name}/sub/b.py"]

    def test_an_added_and_a_removed_file_are_both_named(self, tmp_path):
        _tree(tmp_path, {"a.py": "x = 1\n", "gone.py": "z\n"})
        snap = RSD.Snapshot([str(tmp_path)])
        (tmp_path / "gone.py").unlink()
        _tree(tmp_path, {"new.py": "n\n"})
        assert snap.changed() == [f"{tmp_path.name}/gone.py", f"{tmp_path.name}/new.py"]

    def test_identical_rewrite_is_not_a_change(self, tmp_path):
        """CONTENT, NOT MTIME: a redeploy that rewrites the same bytes touches
        every mtime and changes nothing that runs. Keyed on mtime this gate
        would block after every routine bootstrap and be switched off.

        The mtime is moved by hand AFTER the rewrite. Letting the write set it
        raced the kernel clock: on the Linux runner (pipeline #6658) the create
        and the rewrite fell into one timestamp tick, the premise "mtime
        differs" was false, and the test reddened on its premise while the gate
        it describes was right. NTFS hands out 100 ns stamps, so Windows never
        showed it.
        """
        _tree(tmp_path, {"a.py": "x = 1\n"})
        snap = RSD.Snapshot([str(tmp_path)])
        before = os.stat(tmp_path / "a.py").st_mtime_ns
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        later = before + 5_000_000_000
        os.utime(tmp_path / "a.py", ns=(later, later))
        assert os.stat(tmp_path / "a.py").st_mtime_ns != before
        assert snap.changed() == []

    def test_pycache_and_non_python_files_are_not_compared(self, tmp_path):
        _tree(tmp_path, {"a.py": "x\n", "__pycache__/a.cpython-311.pyc": "old", "cfg.json": "{}"})
        snap = RSD.Snapshot([str(tmp_path)])
        _tree(tmp_path, {"__pycache__/a.cpython-311.pyc": "new", "cfg.json": "{1}", "note.md": "m"})
        assert snap.changed() == []
        assert set(snap.taken[str(tmp_path)]) == {"a.py"}

    def test_several_roots_are_reported_separately(self, tmp_path):
        a, b = tmp_path / "scripts", tmp_path / "mcp"
        _tree(a, {"g.py": "1\n"})
        _tree(b, {"server.py": "2\n"})
        snap = RSD.Snapshot([str(a), str(b)])
        _tree(b, {"server.py": "3\n"})
        assert snap.changed() == ["mcp/server.py"]


class TestRecordStartIsAReference:
    """A reference any caller can move is not a reference."""

    def test_first_call_wins_and_a_second_call_does_not_move_it(self, tmp_path, monkeypatch):
        monkeypatch.setattr(RSD, "_START", None)
        _tree(tmp_path, {"a.py": "1\n"})
        first = RSD.record_start(str(tmp_path))
        _tree(tmp_path, {"a.py": "2\n"})
        second = RSD.record_start(str(tmp_path))
        assert second is first
        assert first.changed() == [f"{tmp_path.name}/a.py"]

    def test_a_new_root_is_added_without_retaking_the_old_one(self, tmp_path, monkeypatch):
        monkeypatch.setattr(RSD, "_START", None)
        a, b = tmp_path / "a", tmp_path / "b"
        _tree(a, {"x.py": "1\n"})
        _tree(b, {"y.py": "1\n"})
        RSD.record_start(str(a))
        _tree(a, {"x.py": "2\n"})  # changes BEFORE b is named must stay visible
        RSD.record_start(str(b))
        assert RSD.changed_since_start() == ["a/x.py"]

    def test_the_module_snapshots_its_own_tree_at_import(self):
        snap = RSD.record_start()
        own = os.path.dirname(os.path.abspath(RSD.__file__))
        assert own in snap.taken
        assert "running_source_drift.py" in snap.taken[own]

    def test_a_missing_extra_root_is_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setattr(RSD, "_START", None)
        snap = RSD.record_start(str(tmp_path / "absent"))
        assert all(os.path.isdir(r) for r in snap.roots)


class TestGateThirdLink:
    """`run_bootstrap_drift_gate` refuses a stale process even when disk and
    source agree — the exact state a redeploy leaves a running server in."""

    def _synthetic_in_sync_project(self, tmp_path, monkeypatch):
        (tmp_path / ".tausik").mkdir()
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
        _tree(tmp_path / "scripts", {"a.py": "x\n"})
        _tree(tmp_path / ".claude" / "scripts", {"a.py": "x\n"})

    def test_in_sync_and_fresh_passes_and_says_so(self, tmp_path, monkeypatch):
        self._synthetic_in_sync_project(tmp_path, monkeypatch)
        run_dir = tmp_path / "running"
        _tree(run_dir, {"gate.py": "v1\n"})
        monkeypatch.setattr(RSD, "_START", RSD.Snapshot([str(run_dir)]))
        from gate_bootstrap_drift import run_bootstrap_drift_gate

        passed, msg = run_bootstrap_drift_gate()
        assert passed is True
        assert "runs the copy that is on disk" in msg

    def test_a_file_changed_after_start_blocks_with_the_restart_remedy(self, tmp_path, monkeypatch):
        self._synthetic_in_sync_project(tmp_path, monkeypatch)
        run_dir = tmp_path / "running"
        _tree(run_dir, {"gate.py": "v1\n"})
        monkeypatch.setattr(RSD, "_START", RSD.Snapshot([str(run_dir)]))
        _tree(run_dir, {"gate.py": "v2\n"})  # the redeploy, under a live process
        from gate_bootstrap_drift import run_bootstrap_drift_gate

        passed, msg = run_bootstrap_drift_gate()
        assert passed is False
        assert "Stale process" in msg
        assert "running/gate.py" in msg
        assert "restart" in msg.lower()
        assert "task done" in msg  # the CLI alternative is named too

    def test_stale_wins_over_in_sync_disk(self, tmp_path, monkeypatch):
        """Disk and source agree; the process does not. 'No drift' here would
        be the most misleading answer the gate could give."""
        self._synthetic_in_sync_project(tmp_path, monkeypatch)
        run_dir = tmp_path / "running"
        _tree(run_dir, {"gate.py": "v1\n"})
        monkeypatch.setattr(RSD, "_START", RSD.Snapshot([str(run_dir)]))
        _tree(run_dir, {"gate.py": "v2\n"})
        from gate_bootstrap_drift import run_bootstrap_drift_gate

        passed, msg = run_bootstrap_drift_gate()
        assert passed is False and "no bootstrap drift" not in msg.lower()


def test_a_real_child_process_sees_the_edit_made_under_it(tmp_path):
    """End to end, in a separate interpreter: the process records its start,
    the parent edits a file under it, the process reports the change. This is
    the session #191 scenario with the server replaced by a plain interpreter."""
    run_dir = tmp_path / "profile"
    _tree(run_dir, {"gate_registry.py": "GATES = 8\n"})
    driver = (
        "import sys, os\n"
        f"sys.path.insert(0, {SCRIPTS!r})\n"
        "import running_source_drift as r\n"
        f"snap = r.Snapshot([{str(run_dir)!r}])\n"
        "print('READY', flush=True)\n"
        "sys.stdin.readline()\n"
        "print('CHANGED', snap.changed(), flush=True)\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", driver],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert proc.stdout is not None and proc.stdin is not None
    assert proc.stdout.readline().strip() == "READY"
    _tree(run_dir, {"gate_registry.py": "GATES = 9\n"})  # the redeploy
    proc.stdin.write("go\n")
    proc.stdin.flush()
    out, _ = proc.communicate(timeout=30)
    assert "CHANGED ['profile/gate_registry.py']" in out


def test_the_server_pins_its_start_at_the_top_of_main():
    """Wiring ratchet: the module can only report what it was told to watch,
    and a server that never called `record_start` would have the blind spot
    the docstring declares. The call must sit in `main`, before the tools."""
    with open(SERVER, encoding="utf-8") as fh:
        body = fh.read()
    main_at = body.index("def main():")
    call_at = body.index("running_source_drift.record_start(")
    serve_at = body.index("from mcp.server import Server")
    assert main_at < call_at < serve_at


@pytest.mark.parametrize("name", ["snapshot", "Snapshot", "record_start", "changed_since_start"])
def test_public_surface_is_exactly_what_the_gate_uses(name):
    assert callable(getattr(RSD, name))
