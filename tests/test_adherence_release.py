"""Release-level acceptance for the 1.11.8 adherence gate."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

import adherence_release as release
from backend_schema import SCHEMA_VERSION
from test_migrations import V1_SCHEMA


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "adherence"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "release@example.invalid")
    _git(tmp_path, "config", "user.name", "Release Gate")
    (tmp_path / "tracked.txt").write_text("frozen\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-m", "frozen")
    return tmp_path


def test_git_identity_binds_commit_and_tree_and_refuses_relevant_dirt(repo):
    identity = release.git_identity(repo, ("tracked.txt",))
    assert identity == {
        "commit_sha": _git(repo, "rev-parse", "HEAD"),
        "tree_sha": _git(repo, "rev-parse", "HEAD^{tree}"),
    }
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(release.ReleaseGateError, match="relevant tree is dirty"):
        release.git_identity(repo, ("tracked.txt",))


def test_git_identity_refuses_untracked_relevant_artifact(repo):
    (repo / "new.txt").write_text("unreviewed\n", encoding="utf-8")
    with pytest.raises(release.ReleaseGateError, match="new.txt"):
        release.git_identity(repo, ("new.txt",))


def test_immutable_worktree_executes_the_exact_committed_snapshot(repo):
    _git(repo, "config", "core.autocrlf", "true")
    commit = _git(repo, "rev-parse", "HEAD")
    with release.immutable_worktree(repo, commit) as snapshot:
        assert (snapshot / "tracked.txt").read_bytes() == b"frozen\n"
        assert _git(snapshot, "rev-parse", "HEAD") == commit
    assert _git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


def test_contract_phases_separate_rejected_sentinels_from_green_acceptance():
    phases = release.evaluator_self_test(ROOT, "a" * 40)
    negative = phases["negative_control"]
    acceptance = phases["acceptance"]
    assert negative["accepted"]
    assert negative["counts"]["failed"] == 0
    assert negative["counts"]["passed"] == negative["counts"]["expected"]
    assert acceptance["accepted"]
    assert acceptance["counts"]["collected"] > 0
    assert all(metric["passed"] for metric in acceptance["metrics"].values())


def test_fixture_load_is_bound_to_the_supplied_snapshot(tmp_path):
    fixture = tmp_path / "tests" / "fixtures" / "adherence"
    fixture.mkdir(parents=True)
    (fixture / "sample.json").write_text('{"source":"snapshot"}\n', encoding="utf-8")
    assert release._load(tmp_path, "sample.json") == {"source": "snapshot"}


def test_frozen_manifest_locks_migrations_v82_through_v86_and_contract_files():
    frozen = release.verify_frozen_artifacts(ROOT)
    files = frozen["files"]
    assert {f"scripts/backend_migrations_v{version}.py" for version in range(82, 87)} <= set(files)
    assert "scripts/adherence_release.py" in files
    assert len(frozen["manifest_sha256"]) == 64


def test_frozen_manifest_detects_a_changed_file(tmp_path, monkeypatch):
    source = tmp_path / "frozen.py"
    source.write_text("old\n", encoding="utf-8")
    manifest = {"files": {"frozen.py": hashlib.sha256(source.read_bytes()).hexdigest()}}
    monkeypatch.setattr(release, "_load", lambda root, name: manifest)
    source.write_text("new\n", encoding="utf-8")
    with pytest.raises(release.ReleaseGateError, match="frozen.py"):
        release.verify_frozen_artifacts(tmp_path)


def test_frozen_manifest_hash_is_independent_of_checkout_newlines(tmp_path, monkeypatch):
    source = tmp_path / "frozen.py"
    source.write_bytes(b"first\r\nsecond\r\n")
    manifest = {"files": {"frozen.py": hashlib.sha256(b"first\nsecond\n").hexdigest()}}
    monkeypatch.setattr(release, "_load", lambda root, name: manifest)
    assert release.verify_frozen_artifacts(tmp_path)["files"] == manifest["files"]


def test_projection_hash_refuses_one_missing_required_artifact(tmp_path):
    (tmp_path / ".codex").mkdir()
    with pytest.raises(release.ReleaseGateError, match="missing"):
        release._projection_rows(tmp_path)


def test_native_lane_refuses_changed_exact_node_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "_collect_nodes", lambda root, files: ["tests/a.py::test_a"])
    with pytest.raises(release.ReleaseGateError, match="collection changed"):
        release._pytest_lane(
            tmp_path,
            "adversarial",
            {"count": 1, "nodes_sha256": "0" * 64},
            ("tests/a.py",),
        )


@pytest.mark.parametrize("summary", ["3 skipped", "4 passed, 1 deselected"])
def test_native_lane_refuses_partial_or_deselected_execution(tmp_path, monkeypatch, summary):
    nodes = [f"tests/a.py::test_{index}" for index in range(4)]
    monkeypatch.setattr(release, "_collect_nodes", lambda root, files: nodes)
    completed = subprocess.CompletedProcess([], 0, stdout=summary, stderr="")
    monkeypatch.setattr(release.subprocess, "run", lambda *args, **kwargs: completed)
    expected = {"count": 4, "nodes_sha256": release.artifact_hash(nodes)}
    with pytest.raises(release.ReleaseGateError, match="failed or collected zero"):
        release._pytest_lane(tmp_path, "adversarial", expected, ("tests/a.py",))


@pytest.mark.parametrize(
    ("program", "timeout"),
    [
        ("raise SystemExit(7)", 2.0),
        ("import time; time.sleep(2)", 0.05),
        ("print('not-json')", 2.0),
        ("", 2.0),
    ],
)
def test_native_stop_failures_are_never_hard_enforcement(program, timeout):
    verdict = release.run_native_stop_probe(
        [release.sys.executable, "-c", program], payload={}, timeout=timeout
    )
    assert not verdict.enforced


def test_advisory_only_report_is_release_blocking(repo, monkeypatch):
    monkeypatch.setattr(
        release, "git_identity", lambda root: {"commit_sha": "a" * 40, "tree_sha": "b" * 40}
    )
    monkeypatch.setattr(release, "evaluator_self_test", lambda root, commit: {"accepted": True})
    monkeypatch.setattr(release, "verify_frozen_artifacts", lambda root: {"files": {}})
    monkeypatch.setattr(release, "projection_evidence", lambda root: {"sha256": "c" * 64})
    with pytest.raises(release.ReleaseGateError, match="advisory-only"):
        release.build_report(repo, run_native=False)


def test_release_manifest_is_canonical_json_with_exact_hashes():
    manifest = json.loads((FIXTURES / "release-manifest-v1.json").read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    assert manifest["change_rule"] == "version-bump-and-release-gate"
    assert all(len(value) == 64 for value in manifest["files"].values())


def test_fresh_process_resumes_exact_first_incomplete_step(tmp_path):
    """The writer exits before a separate reader derives the durable resume action."""
    db_path = tmp_path / "tausik.db"
    scripts = str(ROOT / "scripts")
    writer = "\n".join(
        (
            "import json, sys",
            "sys.path.insert(0, sys.argv[1])",
            "from project_backend import SQLiteBackend",
            "from tausik_utils import utcnow_iso",
            "be = SQLiteBackend(sys.argv[2])",
            "be.session_start('release-writer')",
            "now = utcnow_iso()",
            "plan = json.dumps([{'step':'implement','done':True},{'step':'verify','done':False}])",
            "be._ex(\"INSERT INTO tasks(slug,title,status,complexity,plan,created_at,updated_at) VALUES(?,?,?,?,?,?,?)\", ('release-resume','Release resume','active','complex',plan,now,now))",
            "be._ex(\"INSERT INTO task_continuity_state(task_slug,package_fingerprint,first_incomplete_step,last_evidence_ref,updated_at) VALUES(?,?,?,?,?)\", ('release-resume','f'*64,2,'reason:1',now))",
            "be.close()",
        )
    )
    first = subprocess.run(
        [release.sys.executable, "-c", writer, scripts, str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert first.returncode == 0, first.stderr

    reader = "\n".join(
        (
            "import json, sys",
            "sys.path.insert(0, sys.argv[1])",
            "from project_backend import SQLiteBackend",
            "from work_continuity import continuity_projection",
            "be = SQLiteBackend(sys.argv[2])",
            "print(json.dumps(continuity_projection(be, 'release-resume'), sort_keys=True))",
            "be.close()",
        )
    )
    second = subprocess.run(
        [release.sys.executable, "-c", reader, scripts, str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert second.returncode == 0, second.stderr
    projection = json.loads(second.stdout)
    assert projection["first_incomplete_step"] == 2
    assert projection["last_verified_evidence"] == "reason:1"
    assert projection["resume_action"] == ".tausik/tausik task start release-resume --package"


def test_real_database_restarts_after_every_version_from_v81_to_latest(tmp_path):
    """Exercise the field shape: an on-disk legacy DB and one process per migration."""
    db_path = tmp_path / "tausik.db"
    conn = sqlite3.connect(db_path)
    conn.isolation_level = None
    conn.executescript(V1_SCHEMA)
    conn.execute(
        "INSERT INTO tasks(slug,title,status,created_at,updated_at) VALUES(?,?,?,?,?)",
        ("legacy", "legacy-readable", "planning", "2026-01-01", "2026-01-01"),
    )
    conn.close()

    scripts = str(ROOT / "scripts")
    program = "\n".join(
        (
            "import sqlite3, sys",
            "sys.path.insert(0, sys.argv[1])",
            "import backend_migrations as migrations",
            "path, target = sys.argv[2], int(sys.argv[3])",
            "migrations.MIGRATIONS = {v: sql for v, sql in migrations.MIGRATIONS.items() if v <= target}",
            "conn = sqlite3.connect(path)",
            "conn.isolation_level = None",
            "row = conn.execute(\"SELECT value FROM meta WHERE key='schema_version'\").fetchone()",
            "current = int(row[0]) if row else 1",
            "assert migrations.run_migrations(conn, current) == target",
            "assert migrations.run_migrations(conn, target) == target",
            "assert not conn.execute('PRAGMA foreign_key_check').fetchall()",
            "conn.close()",
        )
    )
    observed = []
    for target in range(81, SCHEMA_VERSION + 1):
        result = subprocess.run(
            [release.sys.executable, "-c", program, scripts, str(db_path), str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        conn = sqlite3.connect(db_path)
        assert conn.execute("SELECT title FROM tasks WHERE slug='legacy'").fetchone()[0] == (
            "legacy-readable"
        )
        assert (
            int(conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0])
            == target
        )
        conn.close()
        observed.append(target)

    assert observed == list(range(81, SCHEMA_VERSION + 1))
