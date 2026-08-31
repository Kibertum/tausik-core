"""A task's own export file, subtracted from the coverage its receipt claims.

verify-handle-dies-on-a-tasks-own-export-file. Found in session #191 while
closing `four-accepted-adrs-were-never-assessed` and reproduced twice: a task
that named `tausik/tasks/<slug>.md` in `--relevant-files` could not be closed by
any sequence of commands. The verify run writes into the task (declared scope,
run number, receipt), the exporter re-serializes the task from that write, and
the handle presented a moment later covers a file the act of verifying had
already moved. Observed hashes: 870e9d910c7c -> edd0acd46e7b -> e8d9e08ecc20.

One class per acceptance criterion:

  AC4  non-convergence is REPRODUCED here, not merely described: hashing the
       declared list moves on every run, hashing the coverage does not
  AC1  a coverage that is nothing but the task's own export is refused by a
       message that NAMES that as the cause and gives the remedy
  AC3a the close a task actually needs: own export declared, own export moved,
       handle accepted
  AC3b THE NEGATIVE, and the one that matters most: a moved SOURCE file is
       still refused. A green here would be a hole in Verify-First far worse
       than the inconvenience this task removes.

Plus the over-subtraction guard: somebody else's export is a legitimate subject
and stays in coverage (`nine-open-tasks-are-invisible-to-release-scope` closed
by declaring nine foreign exports), and the read-side guard that stops an
emptied coverage from becoming the stable empty-marker certificate.

The run rows are assembled from the SAME helpers production uses — the hash is
`compute_files_hash(coverage_files(...))` exactly as `verify_cached_run` writes
it — because a fixture that hand-rolls the value agrees with itself and disagrees
with the code under test, which is how this area's earlier defects stayed green.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
import crypto_sign  # noqa: E402
import verify_handle as vh  # noqa: E402
from backend_schema_gate_runs import GATE_RUNS_SQL  # noqa: E402
from conftest import canonical_ddl  # noqa: E402
from crypto_receipt import build_receipt  # noqa: E402
from verify_cache import _build_cache_command, has_fresh_verify_run, resolve_gate_signature  # noqa: E402
from verify_files_hash import compute_files_hash  # noqa: E402
from verify_handle_check import check_handle  # noqa: E402
from verify_own_export import (  # noqa: E402
    coverage_files,
    declares_own_export,
    own_export_abspath,
    own_export_display,
)

_DDL = canonical_ddl("verification_runs")

SLUG = "records-are-the-product"
SOURCE = "scripts/records.py"


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_DDL + ";")
    c.executescript(GATE_RUNS_SQL)
    yield c
    c.close()


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A keyed project with a real `.tausik/` so the address RESOLVES.

    The directory is created rather than stubbed: `own_export_abspath` derives
    its answer from `state_triggers.projection_dirs`, which walks up from the
    cwd to a real `.tausik/`. A monkeypatched resolver would test the test.
    """
    os.makedirs(tmp_path / ".tausik", exist_ok=True)
    crypto_keys.init_keys(str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return str(tmp_path)


def _write(root: str, relpath: str, body: str) -> str:
    path = os.path.join(root, relpath.replace("/", os.sep))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return relpath


def _own_export(root: str, slug: str = SLUG, *, body: str = "# run 0\n") -> str:
    """Create the task's own export where the exporter would put it."""
    rel = own_export_display(slug)
    assert rel, "the projection root must resolve inside the fixture"
    _write(root, rel, body)
    return rel


def _record_run(conn, project_dir, *, slug=SLUG, declared, exit_code=0, ttl_s=3600):
    """A green run + signed receipt + minted handle, written production-style."""
    declared = sorted(declared)
    files_hash = compute_files_hash(coverage_files(declared, slug))
    cmd = _build_cache_command("verify", declared)
    ran = _iso(datetime.now(timezone.utc))
    cur = conn.execute(
        "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
        "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
        (slug, "standard", cmd, exit_code, "pytest=PASS", files_hash, ran),
    )
    run_id = int(cur.lastrowid)
    expires_at = vh.compute_expires_at(ran, ttl_s)
    receipt = build_receipt(
        task_slug=slug,
        git_sha=None,
        scope="standard",
        gates=[{"name": "pytest", "passed": True, "severity": "block"}],
        passed=exit_code == 0,
        ran_at=ran,
        files_hash=files_hash,
        files=declared,
        gate_signature=resolve_gate_signature("verify"),
        expires_at=expires_at,
    )
    envelope = crypto_sign.sign_receipt(project_dir, receipt)
    conn.execute(
        "UPDATE verification_runs SET receipt_json = ? WHERE id = ?",
        (json.dumps(envelope, ensure_ascii=True, sort_keys=True), run_id),
    )
    conn.commit()
    return run_id, vh.mint_handle(conn, run_id, expires_at=expires_at)


# ------------------------------------------------------- AC4: non-convergence


class TestNonConvergenceIsReproduced:
    """The original cycle, and the property that ends it."""

    def test_declared_hash_moves_on_every_run_coverage_hash_does_not(self, project):
        export = _own_export(project, body="# run 0\n")
        declared = sorted([SOURCE, export])
        _write(project, SOURCE, "def records():\n    return 1\n")

        raw, covered = [], []
        # Three "runs". Each one rewrites the task's export exactly as verify
        # does — it appends the declared scope, the run number and the receipt.
        for run_no in range(3):
            _write(project, export, f"# run {run_no}\nscope: {declared}\nreceipt: {run_no}\n")
            raw.append(compute_files_hash(declared))
            covered.append(compute_files_hash(coverage_files(declared, SLUG)))

        # The defect, stated as a measurement: every run pushes the hash
        # further, so no handle minted by run N can ever be redeemed at run N+1.
        assert len(set(raw)) == 3, "declared-list hashing must be shown NOT to converge"
        # The repair: the same three runs agree, because the one file the run
        # itself rewrites is no longer part of what the receipt covers.
        assert len(set(covered)) == 1, "coverage hashing must converge across runs"

    def test_a_source_edit_still_moves_the_coverage_hash(self, project):
        export = _own_export(project)
        declared = sorted([SOURCE, export])
        _write(project, SOURCE, "def records():\n    return 1\n")
        before = compute_files_hash(coverage_files(declared, SLUG))

        _write(project, SOURCE, "def records():\n    return 2\n")
        after = compute_files_hash(coverage_files(declared, SLUG))

        assert before != after, "subtraction must not blind the hash to source"


# ----------------------------------------------- AC3a: the close that must work


class TestOwnExportDeclaredCloses:
    def test_handle_survives_the_run_rewriting_the_tasks_own_export(self, conn, project):
        export = _own_export(project)
        _write(project, SOURCE, "def records():\n    return 1\n")
        declared = sorted([SOURCE, export])
        _run_id, handle = _record_run(conn, project, declared=declared)

        # Between mint and redemption the framework writes into the task again:
        # `task log`, the receipt, the auto-export. This is what used to make the
        # close impossible.
        _write(project, export, "# rewritten by the framework after the run\n" * 4)

        verdict = check_handle(conn, handle, task_slug=SLUG, project_dir=project)
        assert verdict.ok, verdict.reason

    def test_a_foreign_export_stays_inside_the_coverage(self, conn, project):
        """Over-subtraction would be a lie about what was checked.

        A planning task that re-parents ten tasks really does produce those
        files, and the current run does not touch them, so their hash means what
        it says. Only the task's OWN export is bookkeeping.
        """
        export = _own_export(project)
        foreign = _write(project, own_export_display("another-task"), "# other\n")
        declared = sorted([export, foreign])
        _run_id, handle = _record_run(conn, project, declared=declared)

        assert foreign in coverage_files(declared, SLUG)
        _write(project, foreign, "# somebody edited the foreign export\n")

        verdict = check_handle(conn, handle, task_slug=SLUG, project_dir=project)
        assert not verdict.ok
        assert "have changed since" in verdict.reason


# ------------------------------------------- AC3b: the negative, non-negotiable


class TestSourceChangeIsStillRefused:
    def test_moved_source_file_refuses_even_with_own_export_declared(self, conn, project):
        export = _own_export(project)
        _write(project, SOURCE, "def records():\n    return 1\n")
        declared = sorted([SOURCE, export])
        _run_id, handle = _record_run(conn, project, declared=declared)

        # Both move: the framework rewrote the export (harmless) AND the agent
        # edited a declared source file after the gates ran (not harmless).
        _write(project, export, "# rewritten by the framework\n")
        _write(project, SOURCE, "def records():\n    return 999  # after the gates\n")

        verdict = check_handle(conn, handle, task_slug=SLUG, project_dir=project)
        assert not verdict.ok, "a moved source file must never redeem a handle"
        assert "have changed since" in verdict.reason

    def test_the_refusal_names_the_source_and_clears_the_journal(self, conn, project):
        """#409's closing clause: a mixed scope's refusal must name the SOURCE.

        The message that sent session #191 hunting the cache said only that "the
        files this receipt covers have changed". With the export subtracted the
        one thing the reader needs is that it is NOT the export that moved.
        """
        export = _own_export(project)
        _write(project, SOURCE, "def records():\n    return 1\n")
        declared = sorted([SOURCE, export])
        _run_id, handle = _record_run(conn, project, declared=declared)
        _write(project, SOURCE, "def records():\n    return 2\n")

        verdict = check_handle(conn, handle, task_slug=SLUG, project_dir=project)
        assert not verdict.ok
        assert export in verdict.reason
        assert "NOT part of the coverage" in verdict.reason
        assert "source file" in verdict.reason


# ------------------------------------------------ AC1: the refusal names itself


class TestEmptiedCoverageIsNamed:
    def test_declaring_only_the_own_export_is_refused_by_name(self, conn, project):
        export = _own_export(project)
        _run_id, handle = _record_run(conn, project, declared=[export])

        verdict = check_handle(conn, handle, task_slug=SLUG, project_dir=project)
        assert not verdict.ok
        # Names the cause…
        assert export in verdict.reason
        assert "own" in verdict.reason and "export" in verdict.reason
        # …and both remedies, because "declare real files" is wrong advice for a
        # task that genuinely changed no source.
        assert "--relevant-files" in verdict.reason
        assert "--no-file-changes" in verdict.reason

    def test_emptied_coverage_never_certifies_through_the_freshness_lookup(self, conn, project):
        """The hole the subtraction would open if it were taken bare.

        `compute_files_hash([])` is a stable empty-marker no edit moves. The
        guard that stopped it (`if not files`) reads the DECLARED list, which is
        non-empty here — so the coverage has to be asked the same question, or a
        row keyed on the empty marker stays a valid green for its whole TTL
        across arbitrary tree changes.
        """
        export = _own_export(project)
        declared = [export]
        conn.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            (
                SLUG,
                "standard",
                _build_cache_command("verify", declared),
                0,
                "pytest=PASS",
                compute_files_hash([]),
                _iso(datetime.now(timezone.utc)),
            ),
        )
        conn.commit()

        fresh, hit = has_fresh_verify_run(conn, SLUG, declared)
        assert fresh is False and hit is None


# ------------------------------------------------------- the address resolution


class TestAddressIsDerived:
    def test_path_forms_all_resolve_to_the_same_file(self, project):
        export = _own_export(project)
        forms = [
            export,
            export.replace("/", "\\"),
            "./" + export,
            own_export_abspath(SLUG),
        ]
        for form in forms:
            assert coverage_files([form], SLUG) == [], form
            assert declares_own_export([form], SLUG), form

    def test_another_kinds_export_with_the_same_slug_is_not_subtracted(self, project):
        """The subtraction is one FILE, not the slug's name anywhere in the tree."""
        decision = own_export_display(SLUG).replace("/tasks/", "/decisions/")
        assert coverage_files([decision], SLUG) == [decision]

    def test_an_unresolvable_projection_subtracts_nothing(self, tmp_path, monkeypatch):
        """Fail-open here is the STRICT direction — it restores the old refusal.

        No `.tausik/` means no projection root, so nothing is excluded and the
        callers behave exactly as they did before the repair. An unresolvable
        layout costs convenience, never coverage.
        """
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / "nope" / ".tausik"))
        declared = ["tausik/tasks/%s.md" % SLUG, SOURCE]
        assert coverage_files(declared, SLUG) == declared
        assert declares_own_export(declared, SLUG) is False


# ------------------------------------- the WRITE half: what the run records


@pytest.fixture
def no_envelope(monkeypatch):
    """Disable the envelope timeout — these tests drive a stubbed `run_gates`."""
    monkeypatch.setattr(
        "project_config.load_config",
        lambda *a, **k: {"verify_pipeline_timeout_seconds": 0},
    )


def _gate(name="filesize", passed=True, skipped=False):
    return {
        "name": name,
        "severity": "block",
        "passed": passed,
        "skipped": skipped,
        "output": "",
        "duration_ms": 3,
    }


def _run_gates(conn, monkeypatch, declared, *, slug=SLUG, gates=None):
    """Drive `run_gates_with_cache` with the gate layer stubbed out.

    `run_gates` is imported INSIDE the function under test, so the source module
    is what must be patched — binding the name here would measure the stub
    (memory #448).
    """
    import gate_runner
    import service_verification as sv

    results = gates or [_gate()]
    calls = {"n": 0}

    def fake_run(*_a, **_kw):
        calls["n"] += 1
        return all(r["passed"] for r in results if not r.get("skipped")), results

    monkeypatch.setattr(gate_runner, "run_gates", fake_run)
    out = sv.run_gates_with_cache(conn, slug, list(declared), trigger="verify")
    return (*out, calls["n"])


class TestRecordedHashIsTakenOverCoverage:
    def test_the_row_stores_the_coverage_hash_not_the_declared_one(
        self, conn, project, monkeypatch, no_envelope
    ):
        export = _own_export(project)
        _write(project, SOURCE, "def records():\n    return 1\n")
        declared = sorted([SOURCE, export])

        _run_gates(conn, monkeypatch, declared)

        stored = conn.execute(
            "SELECT files_hash FROM verification_runs WHERE task_slug=?", (SLUG,)
        ).fetchone()[0]
        assert stored == compute_files_hash(coverage_files(declared, SLUG))
        assert stored != compute_files_hash(declared), (
            "the write side must subtract too — a hash taken over the declared "
            "list is the defect this task exists for"
        )

    def test_a_second_verify_hits_the_cache_after_the_run_moved_the_export(
        self, conn, project, monkeypatch, no_envelope
    ):
        """The cycle, end to end, through the real function.

        Run one records. The framework then rewrites the task's export exactly
        as `task log` and the receipt do. Run two must reuse run one instead of
        re-executing gates — before the repair it never could.
        """
        export = _own_export(project)
        _write(project, SOURCE, "def records():\n    return 1\n")
        declared = sorted([SOURCE, export])

        _p1, _r1, status1, calls1 = _run_gates(conn, monkeypatch, declared)
        assert status1 == "miss" and calls1 == 1

        _write(project, export, "# the run wrote its own receipt in here\n" * 3)

        _p2, _r2, status2, calls2 = _run_gates(conn, monkeypatch, declared)
        assert status2 == "hit", "the export moving must not invalidate the run"
        assert calls2 == 0, "a hit must not re-execute the gates"

    def test_a_scope_of_only_the_own_export_is_recorded_noncacheable(
        self, conn, project, monkeypatch, no_envelope
    ):
        """`bool(files)` stopped being the question once coverage can differ.

        The gates did run against the declared file, so the row is written —
        observability is not cache eligibility (#146). But it covers nothing, so
        it must never be replayable: `compute_files_hash([])` is the stable
        empty-marker no edit moves.
        """
        export = _own_export(project)

        _run_gates(conn, monkeypatch, [export])

        command = conn.execute(
            "SELECT command FROM verification_runs WHERE task_slug=?", (SLUG,)
        ).fetchone()[0]
        assert command.startswith("noncacheable|"), command

    def test_a_normal_scope_is_still_cacheable(
        self, conn, project, monkeypatch, no_envelope
    ):
        """Negative control: the ordinary path is untouched by the subtraction."""
        _write(project, SOURCE, "def records():\n    return 1\n")

        _run_gates(conn, monkeypatch, [SOURCE])

        command = conn.execute(
            "SELECT command FROM verification_runs WHERE task_slug=?", (SLUG,)
        ).fetchone()[0]
        assert not command.startswith("noncacheable|"), command


class TestFreshnessLookupSubtractsToo:
    def test_a_green_survives_the_run_rewriting_the_export(self, conn, project):
        """The non-handle half of QG-2 must subtract identically.

        If only the handle path did, `task done` without a handle would still be
        trapped in the original cycle — the defect would merely have moved.
        """
        export = _own_export(project)
        _write(project, SOURCE, "def records():\n    return 1\n")
        declared = sorted([SOURCE, export])
        conn.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            (
                SLUG,
                "standard",
                _build_cache_command("verify", declared),
                0,
                "pytest=PASS",
                compute_files_hash(coverage_files(declared, SLUG)),
                _iso(datetime.now(timezone.utc)),
            ),
        )
        conn.commit()

        _write(project, export, "# rewritten by the framework after the run\n" * 3)

        fresh, hit = has_fresh_verify_run(conn, SLUG, declared)
        assert fresh is True and hit is not None

    def test_a_moved_source_file_still_misses(self, conn, project):
        """Negative control for the same lookup."""
        export = _own_export(project)
        _write(project, SOURCE, "def records():\n    return 1\n")
        declared = sorted([SOURCE, export])
        conn.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            (
                SLUG,
                "standard",
                _build_cache_command("verify", declared),
                0,
                "pytest=PASS",
                compute_files_hash(coverage_files(declared, SLUG)),
                _iso(datetime.now(timezone.utc)),
            ),
        )
        conn.commit()

        _write(project, SOURCE, "def records():\n    return 2  # after the gates\n")

        fresh, hit = has_fresh_verify_run(conn, SLUG, declared)
        assert fresh is False and hit is None
