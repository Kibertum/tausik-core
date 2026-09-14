"""What a test RUN reached, recorded as evidence the graph can be asked about.

WHY OBSERVED AND NOT DERIVED. Test selection maps `scripts/foo.py` to
`tests/test_foo.py` by NAME. `CROSSCUTTING_SCOPE` exists because that fails —
a hand-written patch declared four times in session #157 alone. Names cannot see
dynamic dispatch, monkeypatching, or the local-imports-inside-function-bodies
style this codebase uses everywhere. A run can.

MEASURED BEFORE ANY OF THIS (session #236):

    coverage.py            not installed, and cannot be — the project is
                           stdlib-only by a hard constraint
    sys.setprofile         fires and records exactly what a call reaches:
                           `roots_for('.')` gave source_roots.py and ide_utils.py
    installed globally     does NOT survive into pytest — it reported zero files,
                           so the observer has to be a plugin, which is also what
                           gives per-TEST attribution
    one file, 22 tests     5.5s without observation, 14.5s with it

THE SELECTION IS A SUPERSET ON PURPOSE. An incomplete graph plus an exact
selection is a false-green machine: a missed test looks passed, while a
redundant one costs seconds. So the observed edge is ADDED to the name, import
and declared-scope edges — never substituted for them.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO / "scripts"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import observed_coverage as oc  # noqa: E402
from backend_schema_graph import EDGE_LAYERS  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "tests/conftest.py"]


class TestTheObserverIsOffUnlessAskedFor:
    """AC1. The ordinary run must not pay for a graph it is not building."""

    def test_absent_flag_means_disabled(self, monkeypatch):
        monkeypatch.delenv(oc.ENV_FLAG, raising=False)
        assert oc.is_enabled() is False

    def test_any_value_enables_it(self, monkeypatch):
        monkeypatch.setenv(oc.ENV_FLAG, "1")
        assert oc.is_enabled() is True

    def test_the_conftest_hook_checks_the_flag_before_doing_anything(self):
        """Asserted on the source because the alternative — timing an ordinary
        run — measures the machine's mood as much as the code."""
        text = (_REPO / "tests" / "conftest.py").read_text(encoding="utf-8")
        hook = text[text.index("def pytest_runtest_call") :]
        assert "is_enabled()" in hook.split("observer")[0], (
            "the hook must decide before constructing an observer"
        )


class TestTheObserverRecordsWhatWasActuallyReached:
    """AC1, the positive half: an observer that records nothing proves nothing
    about the cost of one that does."""

    def test_it_sees_a_file_a_call_reaches(self, tmp_path):
        module = tmp_path / "reached.py"
        module.write_text("def touched():\n    return 1\n", encoding="utf-8")
        sys.path.insert(0, str(tmp_path))
        try:
            observer = oc.Observer(str(tmp_path))
            observer.start()
            try:
                import reached  # noqa: PLC0415

                reached.touched()
            finally:
                touched = observer.stop()
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("reached", None)
        assert "reached.py" in touched

    def test_it_stops_recording_after_stop(self, tmp_path):
        observer = oc.Observer(str(tmp_path))
        observer.start()
        observer.stop()
        assert sys.getprofile() is None or sys.getprofile() is not observer._hook

    def test_stop_forgets_so_one_test_cannot_inherit_another(self, tmp_path):
        observer = oc.Observer(str(tmp_path))
        observer.start()
        observer.stop()
        observer.start()
        assert observer.stop() == set()


class TestAPseudoPathIsNeverAnArtifact:
    """Found in the first trial run: frozen stdlib modules report `<frozen os>`
    as their filename, and `relpath` treats that as a relative name UNDER the
    root — so `<frozen codecs>` was recorded as a repository file. An artifact
    no query can ever resolve is worse than a missing one."""

    @pytest.mark.parametrize(
        "candidate",
        [
            pytest.param("<frozen os>", id="frozen_module"),
            pytest.param("<string>", id="exec_string"),
            pytest.param("relative/thing.py", id="already_relative"),
        ],
    )
    def test_it_is_refused(self, candidate):
        assert oc._repo_relative(candidate, str(_REPO)) is None

    def test_a_real_file_under_the_root_is_accepted(self):
        real = str(_REPO / "scripts" / "observed_coverage.py")
        # The observer's own module is refused BY NAME, so this asserts the
        # positive path with a different file.
        real = str(_REPO / "scripts" / "symbol_index.py")
        assert oc._repo_relative(real, str(_REPO)) == "scripts/symbol_index.py"

    def test_a_file_outside_the_root_is_refused(self, tmp_path):
        outside = tmp_path / "elsewhere.py"
        outside.write_text("x = 1\n", encoding="utf-8")
        assert oc._repo_relative(str(outside), str(_REPO)) is None


class TestTheEdgeCarriesItsOwnProvenance:
    """AC3. Observed coverage is neither an inference from history nor somebody's
    statement, so it gets a layer of its own rather than borrowing one."""

    def test_the_layer_exists_in_the_closed_list(self):
        assert "observed_coverage" in EDGE_LAYERS

    def test_it_is_not_one_of_the_declared_layers(self):
        """Borrowing `declared_crosscutting` would have avoided a migration and
        told a lie: the graph's entire discipline is that an inference and a
        record never share a number."""
        assert "observed_coverage" not in {
            layer for layer in EDGE_LAYERS if layer.startswith("declared_")
        }
        assert "observed_coverage" != "git_cochange"


class TestIngestionTurnsObservationsIntoEdges:
    """AC5, and the two shapes that would make the graph lie if stored."""

    @pytest.fixture
    def svc(self, tmp_path):
        s = ProjectService(SQLiteBackend(str(tmp_path / "g.db")))
        yield s
        s.be.close()

    def _project(self, tmp_path, rows: list[tuple[str, str]]) -> Path:
        root = tmp_path / "proj"
        (root / "tests").mkdir(parents=True)
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "thing.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (root / "tests" / "test_thing.py").write_text("def test_f():\n    pass\n", encoding="utf-8")
        (root / ".tausik").mkdir()
        out = root / ".tausik" / "observed_coverage.jsonl"
        out.write_text(
            "".join(json.dumps({"test": t, "file": f}) + "\n" for t, f in rows),
            encoding="utf-8",
        )
        return root

    def test_an_observation_becomes_a_covers_edge(self, svc, tmp_path, monkeypatch):
        root = self._project(tmp_path, [("tests/test_thing.py::test_f", "scripts/thing.py")])
        monkeypatch.chdir(root)
        from project_cli_graph import ingest_observed

        result = ingest_observed(svc, str(root))
        assert result["edges"] == 1
        rows = svc.be._q(
            "SELECT e.relation, e.layer, e.observations, s.path AS src, d.path AS dst "
            "FROM artifact_edges e "
            "JOIN artifacts s ON s.id = e.source_artifact_id "
            "JOIN artifacts d ON d.id = e.target_artifact_id"
        )
        assert len(rows) == 1
        assert rows[0]["relation"] == "covers"
        assert rows[0]["layer"] == "observed_coverage"
        assert rows[0]["src"] == "tests/test_thing.py"
        assert rows[0]["dst"] == "scripts/thing.py"

    def test_the_test_file_reaching_itself_is_not_an_edge(self, svc, tmp_path, monkeypatch):
        """The observer records the test file honestly — it is where the test
        lives. Storing that as an edge would say a file covers itself."""
        root = self._project(
            tmp_path,
            [
                ("tests/test_thing.py::test_f", "tests/test_thing.py"),
                ("tests/test_thing.py::test_f", "scripts/thing.py"),
            ],
        )
        monkeypatch.chdir(root)
        from project_cli_graph import ingest_observed

        assert ingest_observed(svc, str(root))["edges"] == 1

    def test_observations_count_the_tests_not_the_lines(self, svc, tmp_path, monkeypatch):
        root = self._project(
            tmp_path,
            [
                ("tests/test_thing.py::test_a", "scripts/thing.py"),
                ("tests/test_thing.py::test_b", "scripts/thing.py"),
                ("tests/test_thing.py::test_c", "scripts/thing.py"),
            ],
        )
        monkeypatch.chdir(root)
        from project_cli_graph import ingest_observed

        ingest_observed(svc, str(root))
        row = svc.be._q1("SELECT observations FROM artifact_edges")
        assert row["observations"] == 3

    def test_a_file_that_no_longer_exists_is_not_stored(self, svc, tmp_path, monkeypatch):
        """An observation is a record of the PAST. A file deleted since must not
        reappear as an artifact — the graph would then know a file the tree does
        not have."""
        root = self._project(
            tmp_path, [("tests/test_thing.py::test_f", "scripts/deleted_since.py")]
        )
        monkeypatch.chdir(root)
        from project_cli_graph import ingest_observed

        assert ingest_observed(svc, str(root))["edges"] == 0

    def test_no_observation_file_is_absence_not_an_error(self, svc, tmp_path, monkeypatch):
        root = tmp_path / "empty"
        root.mkdir()
        monkeypatch.chdir(root)
        from project_cli_graph import ingest_observed

        assert ingest_observed(svc, str(root)) == {"pairs": 0, "edges": 0, "tests": 0}


class TestSelectionUsesTheGraphAndKeepsTheNamesAsFallback:
    """AC4 and AC7. The resolver is SUBORDINATED, not replaced: a graph with
    nothing observed must select exactly what it selected before."""

    def test_an_empty_graph_changes_nothing(self, tmp_path, monkeypatch):
        from gate_test_resolver import _observed_tests_for

        monkeypatch.chdir(tmp_path)
        assert _observed_tests_for(str(tmp_path), ["scripts/thing.py"]) == set()

    def test_an_unreadable_database_is_absence_not_a_crash(self, tmp_path):
        from gate_test_resolver import _observed_tests_for

        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_bytes(b"not a database")
        assert _observed_tests_for(str(tmp_path), ["scripts/thing.py"]) == set()

    def test_an_observed_edge_selects_a_test_the_names_would_miss(self, tmp_path, monkeypatch):
        """THE POINT OF THE WHOLE TASK. `scripts/thing.py` and
        `tests/test_something_else.py` share no name and no import, so every
        existing edge misses the pair. The observation does not."""
        from gate_test_resolver import _observed_tests_for

        root = tmp_path / "proj"
        (root / "tests").mkdir(parents=True)
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "thing.py").write_text("x = 1\n", encoding="utf-8")
        (root / "tests" / "test_something_else.py").write_text("x = 1\n", encoding="utf-8")
        (root / ".tausik").mkdir()

        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            src = svc.be.artifact_upsert("tests/test_something_else.py", "test", "h1")
            dst = svc.be.artifact_upsert("scripts/thing.py", "code", "h2")
            svc.be.artifact_edge_add(src, dst, "covers", "observed_coverage", 1.0)
        finally:
            svc.be.close()

        monkeypatch.chdir(root)
        found = _observed_tests_for(str(root), ["scripts/thing.py"])
        assert found == {"tests/test_something_else.py"}

    def test_the_resolver_adds_the_observed_test_to_its_own_answer(self, tmp_path, monkeypatch):
        """Additive, not substitutive: the name-based answer must survive."""
        from gate_test_resolver import resolve_test_files_for_relevant

        root = tmp_path / "proj"
        (root / "tests").mkdir(parents=True)
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "thing.py").write_text("x = 1\n", encoding="utf-8")
        (root / "tests" / "test_thing.py").write_text("x = 1\n", encoding="utf-8")
        (root / "tests" / "test_unrelated_name.py").write_text("x = 1\n", encoding="utf-8")
        (root / ".tausik").mkdir()

        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            src = svc.be.artifact_upsert("tests/test_unrelated_name.py", "test", "h1")
            dst = svc.be.artifact_upsert("scripts/thing.py", "code", "h2")
            svc.be.artifact_edge_add(src, dst, "covers", "observed_coverage", 1.0)
        finally:
            svc.be.close()

        monkeypatch.chdir(root)
        found = set(resolve_test_files_for_relevant(["scripts/thing.py"], root=str(root)))
        assert "tests/test_thing.py" in found, "the name edge was lost"
        assert "tests/test_unrelated_name.py" in found, "the observed edge did not reach selection"


class TestARecordingFailureNeverBreaksTheRun:
    """The observation is a by-product; the run is the work."""

    def test_an_unwritable_output_is_swallowed(self, tmp_path):
        target = tmp_path / "nope" / "deep" / "out.jsonl"
        os.makedirs(target.parent, exist_ok=True)
        target.parent.chmod(0o500)
        try:
            oc.record(str(target), "tests/x.py::t", {"scripts/y.py"})
        finally:
            target.parent.chmod(0o700)

    def test_a_torn_line_does_not_discard_its_neighbours(self, tmp_path):
        out = tmp_path / "obs.jsonl"
        out.write_text(
            json.dumps({"test": "t1", "file": "a.py"})
            + "\n"
            + "{not json at all\n"
            + json.dumps({"test": "t2", "file": "b.py"})
            + "\n",
            encoding="utf-8",
        )
        assert list(oc.read(str(out))) == [("t1", "a.py"), ("t2", "b.py")]
