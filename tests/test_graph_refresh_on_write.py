"""The graph stays fresh because the write hook refreshes it — in its own process.

MEASURED (session #235, live tree, live 66 MB database):

    a hook process, start to finish     54 ms — almost all of it Python starting
    re-indexing one file, the work      0.47 ms
    parsing the largest file's AST      1.62 ms
    a full `graph build`                ~9,000 ms

    auto_format before this task        68 ms
    ... with the refresh through        301 ms — `SQLiteBackend` runs
        `SQLiteBackend`                  `init_schema` on open and
                                         `wal_checkpoint(TRUNCATE)` on close
    ... with a raw sqlite3 UPDATE       279 ms
    ... after removing the per-write    50 ms — FASTER than before the task
        journal entry (190 ms of CLI)

THE SHAPE THAT FOLLOWS FROM THOSE NUMBERS: the work is milliseconds and a
process is tens of milliseconds, so re-indexing rides inside a hook that already
runs and never becomes a hook of its own. And it is not a gate: a blocking check
on a SECONDARY index would stop primary work, and a false block on routine
teaches circumvention (convention #291). Quiet on write, loud on query.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO / "scripts"), str(_REPO / "scripts" / "hooks"), str(_REPO / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import graph_refresh  # noqa: E402
from consumer_layout import build_consumer_project  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/hooks/", "bootstrap/"]

_HOOK = _REPO / "scripts" / "hooks" / "auto_format.py"


def _project(tmp_path: Path) -> Path:
    """A project with a TAUSIK database and one indexed file."""
    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True)
    (root / "app").mkdir()
    (root / "app" / "orders.py").write_text(
        "def place_order(cart):\n    return sum(cart)\n", encoding="utf-8"
    )
    svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
    try:
        svc.graph_index_paths(["app/orders.py"], root=str(root))
    finally:
        svc.be.close()
    return root


def _stored(root: Path, rel: str) -> dict | None:
    with sqlite3.connect(str(root / ".tausik" / "tausik.db")) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM artifacts WHERE path = ?", (rel,)).fetchone()
    return dict(row) if row else None


def _fire(root: Path, file_path: Path) -> subprocess.CompletedProcess:
    payload = json.dumps(
        {"tool_name": "Write", "session_id": "t", "tool_input": {"file_path": str(file_path)}}
    )
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(root),
        env={**os.environ, "PYTHONUTF8": "1", "CLAUDE_PROJECT_DIR": str(root)},
        timeout=300,
    )


class TestNoSecondProcessWasAdded:
    """AC1. The work is 0.47 ms; a process of its own is 54 ms. Overhead of
    thirty times the work, plus a second thing to deploy and keep in parity."""

    @pytest.mark.parametrize("ide", ["claude", "qwen"])
    def test_the_refresh_is_not_registered_as_a_hook_anywhere(self, tmp_path, ide):
        sys.path.insert(0, str(_REPO / "bootstrap"))
        target = tmp_path / ide
        target.mkdir()
        if ide == "claude":
            from bootstrap_generate import generate_settings_claude

            generate_settings_claude(str(target), str(tmp_path), lib_dir=str(_REPO))
        else:
            from bootstrap_qwen import generate_settings_qwen

            generate_settings_qwen(
                str(target), str(tmp_path), venv_python=sys.executable, lib_dir=str(_REPO)
            )
        data = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        commands = [
            hook.get("command", "")
            for entries in data["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks") or []
        ]
        assert not any("graph_refresh" in c for c in commands), (
            f"{ide} runs the refresh as its own process — the measurement says the "
            "overhead would be thirty times the work"
        )
        assert any("auto_format" in c for c in commands), f"{ide} lost its write hook"

    def test_the_module_is_a_function_not_an_entry_point(self):
        """A module with a `__main__` invites being wired up as a hook later."""
        source = (_REPO / "scripts" / "graph_refresh.py").read_text(encoding="utf-8")
        assert '__name__ == "__main__"' not in source


class TestTheStateIndexedIsTheStateOnDiskAfterTheWrite:
    """AC2. A fingerprint taken before formatting would disagree with disk in
    the same instant — a LIE, which is worse than being behind."""

    def test_the_stored_hash_matches_the_file_after_the_hook(self, tmp_path):
        from service_artifact_graph import fingerprint

        root = _project(tmp_path)
        target = root / "app" / "orders.py"
        before = _stored(root, "app/orders.py")
        target.write_text("def place_order(cart, user):\n    return sum(cart)\n", encoding="utf-8")

        assert _fire(root, target).returncode == 0
        after = _stored(root, "app/orders.py")
        assert after is not None
        assert after["content_hash"] != before["content_hash"], "the refresh did not run"
        assert after["content_hash"] == fingerprint("app/orders.py", str(root))

    def test_a_query_then_reports_it_as_fresh(self, tmp_path):
        root = _project(tmp_path)
        target = root / "app" / "orders.py"
        target.write_text("def place_order(cart, user):\n    return 1\n", encoding="utf-8")
        _fire(root, target)

        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            answer = svc.neighbours_of("app/orders.py", root=str(root))
        finally:
            svc.be.close()
        assert answer["known"] is True
        assert answer["stale"] == [], "the file was re-indexed and must not read as stale"


class TestTheCostIsNamedAndGuarded:
    """AC3. A hook that slows every write gets switched off, and then the
    framework ships a stale index with the box ticked — the worst outcome."""

    @staticmethod
    def _commit_floor_ms(tmp_path) -> float:
        """What ONE committed SQLite write costs on this disk — the environment's
        floor. On WSL2 an fsync costs tens of milliseconds and a refresh measured
        44.7 ms against a 10 ms bar (session #260): the disk, not a regression."""
        db = str(tmp_path / "floor.db")
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE t (x)")
        started = time.perf_counter()
        for i in range(10):
            with sqlite3.connect(db) as conn:
                conn.execute("INSERT INTO t VALUES (?)", (i,))
        return (time.perf_counter() - started) * 100

    def test_one_refresh_stays_in_single_digit_milliseconds(self, tmp_path):
        root = _project(tmp_path)
        target = root / "app" / "orders.py"
        graph_refresh.refresh_one(str(root), str(target))  # warm the imports
        floor = self._commit_floor_ms(tmp_path)

        started = time.perf_counter()
        for _ in range(10):
            graph_refresh.refresh_one(str(root), str(target))
        each = (time.perf_counter() - started) * 100
        bar = max(10.0, 20 * floor)
        assert each < bar, (
            f"{each:.1f} ms per refresh against a bar of {bar:.1f} ms (10 ms, or 20× this "
            f"disk's {floor:.2f} ms commit floor). Measured at 0.47 ms of work on a fast "
            "disk; the bar catches an order-of-magnitude regression, not the disk"
        )

    def test_a_tenfold_regression_is_still_caught(self, tmp_path, monkeypatch):
        """NEGATIVE: the floor-relative bar is not a blank cheque."""
        floor = self._commit_floor_ms(tmp_path)
        bar = max(10.0, 20 * floor)
        slow = bar * 10 / 1000  # seconds per call — ten times the bar
        monkeypatch.setattr(graph_refresh, "refresh_one", lambda *a, **k: time.sleep(slow))
        started = time.perf_counter()
        for _ in range(3):
            graph_refresh.refresh_one("x", "y")
        each = (time.perf_counter() - started) * 1000 / 3
        assert each >= bar, "the mocked regression must exceed the bar, or the test proves nothing"

    def test_it_does_not_go_through_the_backend(self):
        """Going through `SQLiteBackend` put the hook at 301 ms against 68 ms:
        opening it runs `init_schema`, closing it checkpoints a 66 MB WAL.

        Asserted by PARSING, not by searching for the name: the module names the
        backend in the comment explaining why it does not use it, and a text
        search cannot tell an explanation from a call. The same shape of mistake
        this project has caught in its own tests before.
        """
        import ast

        tree = ast.parse((_REPO / "scripts" / "graph_refresh.py").read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        assert "SQLiteBackend" not in imported, "the refresh opens the full backend again"
        assert "ProjectService" not in imported
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "SQLiteBackend" not in called
        assert any(
            isinstance(node, ast.Import) and any(a.name == "sqlite3" for a in node.names)
            for node in ast.walk(tree)
        ), "it must talk to the database directly, which is the point"


class TestFailOpenOnTheWorkAndLoudOnTheTruth:
    """AC4 and AC5, the two halves that must both hold."""

    def test_a_broken_index_does_not_fail_the_write(self, tmp_path):
        root = _project(tmp_path)
        (root / ".tausik" / "tausik.db").write_bytes(b"not a database at all")
        target = root / "app" / "orders.py"
        target.write_text("def place_order(cart):\n    return 2\n", encoding="utf-8")

        result = _fire(root, target)
        assert result.returncode == 0, "the graph is secondary; its failure must not block work"
        assert target.read_text(encoding="utf-8").endswith("return 2\n")

    def test_a_refresh_that_could_not_run_leaves_the_artifact_reading_stale(self, tmp_path):
        """The loud half. Nothing is printed on the write — the QUERY tells the
        truth, because it recomputes fingerprints from disk every time."""
        root = _project(tmp_path)
        target = root / "app" / "orders.py"
        target.write_text("def place_order(cart):\n    return 3\n", encoding="utf-8")
        # No hook fires: this is what a failed or skipped refresh looks like.

        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            answer = svc.neighbours_of("app/orders.py", root=str(root))
        finally:
            svc.be.close()
        assert answer["partially_stale"] is True
        assert "app/orders.py" in answer["stale"]

    def test_the_refresh_itself_returns_none_rather_than_raising(self, tmp_path):
        root = _project(tmp_path)
        (root / ".tausik" / "tausik.db").write_bytes(b"garbage")
        assert graph_refresh.refresh_one(str(root), str(root / "app" / "orders.py")) is None


class TestChangesFromOutsideAreCaughtByTheQuery:
    """AC6. `git pull`, another editor, a hand edit — no hook sees those, and
    that is NAMED rather than papered over."""

    def test_an_edit_without_the_hook_shows_up_as_stale(self, tmp_path):
        root = _project(tmp_path)
        (root / "app" / "orders.py").write_text("# rewritten by git pull\n", encoding="utf-8")

        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            answer = svc.neighbours_of("app/orders.py", root=str(root))
        finally:
            svc.be.close()
        assert answer["stale"] == ["app/orders.py"]


class TestTheRefreshNeverWidensTheGraph:
    """AC8. A write that quietly adds artifacts would make the stored count stop
    matching what `graph build` printed, and a count nobody can reproduce is
    worse than a count that is behind."""

    def test_a_file_the_graph_does_not_know_adds_no_row(self, tmp_path):
        root = _project(tmp_path)
        newcomer = root / "app" / "invoices.py"
        newcomer.write_text("def bill():\n    return 0\n", encoding="utf-8")

        assert graph_refresh.refresh_one(str(root), str(newcomer)) is None
        assert _stored(root, "app/invoices.py") is None

    @pytest.mark.parametrize(
        "rel",
        [
            pytest.param(".tausik/config.json", id="framework_state"),
            pytest.param("docs/_generated/constants.json", id="generated"),
        ],
    )
    def test_the_frameworks_own_churn_is_skipped(self, tmp_path, rel):
        """These change on nearly every command — a journal line, a regenerated
        roadmap — so re-indexing them would make the hook busiest exactly when
        the agent is doing bookkeeping rather than work."""
        root = _project(tmp_path)
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        assert graph_refresh.refresh_one(str(root), str(path)) is None

    def test_a_file_outside_the_project_is_ignored(self, tmp_path):
        root = _project(tmp_path)
        outside = tmp_path / "elsewhere.py"
        outside.write_text("x = 1\n", encoding="utf-8")
        assert graph_refresh.refresh_one(str(root), str(outside)) is None


class TestItWorksInAConsumerLayout:
    """AC9. project_dir and lib_dir are different directories there, and six
    defects of that class reached live installations before the fixture existed."""

    def test_the_refresh_finds_the_database_beside_the_project(self, tmp_path):
        proj = build_consumer_project(tmp_path)
        root = Path(getattr(proj, "root", getattr(proj, "project_dir", tmp_path)))
        (root / ".tausik").mkdir(exist_ok=True)
        app = root / "backend" / "api"
        app.mkdir(parents=True, exist_ok=True)
        target = app / "orders.py"
        target.write_text("def place_order(c):\n    return c\n", encoding="utf-8")

        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            svc.graph_index_paths(["backend/api/orders.py"], root=str(root))
        finally:
            svc.be.close()

        target.write_text("def place_order(c, user):\n    return c\n", encoding="utf-8")
        assert graph_refresh.refresh_one(str(root), str(target)) == "backend/api/orders.py"


class TestTheStoredRowMatchesWhatTheBackendWouldHaveWritten:
    """The raw UPDATE is a second way to write the same row, so it is pinned
    against the first. Without this the two drift and nothing notices."""

    def test_kind_and_hash_agree_with_artifact_upsert(self, tmp_path):
        from service_artifact_graph import classify, fingerprint

        root = _project(tmp_path)
        target = root / "app" / "orders.py"
        target.write_text("class OrderService:\n    pass\n", encoding="utf-8")
        graph_refresh.refresh_one(str(root), str(target))
        row = _stored(root, "app/orders.py")

        assert row is not None
        assert row["kind"] == classify("app/orders.py")
        assert row["content_hash"] == fingerprint("app/orders.py", str(root))
        assert row["indexed_at"].endswith("Z"), "timestamp shape must match the backend's"
