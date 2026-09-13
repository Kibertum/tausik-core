"""The coherence lens, held against the two ways a lens like this fails.

A repository-wide review has exactly two failure modes worth testing, and both
are named in the task that asked for it:

  1. IT FINDS NOTHING. On a repository where ten defects were found by hand in
     two days, a lens reporting zero is broken, not vindicated. Silence from a
     detector is indistinguishable from health, which is why it is asserted
     against the LIVE tree rather than a fixture.
  2. NOBODY READS IT. An unranked, unbounded report costs attention and returns
     the feeling of having looked. So volume is capped, findings are ordered by
     risk, and what was NOT examined is stated in the report itself.

CROSSCUTTING_SCOPE is declared below because this walks the whole tree: a change
to any collector it aggregates should select these tests, and no basename
heuristic could ever map `audit_stale_docs.py` to a file called `coherence`.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

CROSSCUTTING_SCOPE = [
    "scripts/repo_coherence.py",
    "scripts/audit_orphan_files.py",
    "scripts/audit_pytest_dedupe.py",
    "scripts/audit_stale_docs.py",
    "scripts/audit_unused_python.py",
    "scripts/audit_translation_drift.py",
    "scripts/audit_closure_evidence.py",
    "scripts/doc_drift_scanners.py",
]

import repo_coherence  # noqa: E402

_ROOT = os.path.join(os.path.dirname(__file__), "..")


@pytest.fixture(scope="module")
def live():
    """The lens run against THIS repository — the only calibration that counts."""
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    db = os.path.join(_ROOT, ".tausik", "tausik.db")
    if not os.path.exists(db):
        pytest.skip("no project database in this checkout")
    svc = ProjectService(SQLiteBackend(db))
    try:
        tasks = svc.be.task_list(limit=100000)
        if not tasks:
            # A bootstrapped but empty database (a fresh clone, CI) is not
            # this repository's record; the calibration below names defects
            # that live in the bookkeeping, and an empty store has none to find.
            pytest.skip("the project database holds no tasks — no record to calibrate against")
        yield repo_coherence.collect(_ROOT, tasks=tasks, service=svc)
    finally:
        svc.be.close()


class TestALensThatFindsNothingIsBroken:
    """AC-5. Ten defects were found here by hand; zero is not a clean bill."""

    def test_the_live_repository_yields_findings(self, live):
        assert live["findings"], (
            "the lens reported nothing on a repository with known defects — "
            "a detector's silence is indistinguishable from health, so this is "
            "read as broken rather than as clean"
        )

    def test_every_collector_actually_ran(self, live):
        """A skipped collector is a NAMED gap, and there should be none here.

        This is the same assertion in the other direction: findings could look
        healthy while half the collectors silently failed.
        """
        assert live["collectors_skipped"] == []
        assert live["collectors_run"] >= 8

    def test_it_sees_the_known_duplicate_test_class(self, live):
        """One of the calibration defects named in the task, by name."""
        kinds = {f["kind"] for f in live["findings"]}
        assert "duplicate_tests" in kinds

    def test_it_sees_the_known_rotted_evidence_class(self, live):
        """The other one this session met in person: closure citations that no
        longer resolve, found by `audit evidence` in a previous shift."""
        kinds = {f["kind"] for f in live["findings"]}
        assert "rotted_closure_evidence" in kinds or "invented_closure_evidence" in kinds


class TestTheThirdCalibrationClassIsDetectable:
    """`doc_number_drift` finds nothing today because the numbers are correct.

    That is the right answer and a bad test, so detectability is proven by
    PLANTING the defect rather than by waiting for one: the collector must turn
    a wrong self-described number into a finding. Without this, "no finding" would
    mean either "no drift" or "collector dead" and nobody could tell which.
    """

    def test_a_wrong_number_in_the_prose_becomes_a_finding(self, monkeypatch, tmp_path):
        import repo_coherence as rc

        def fake_drift(_root):
            return [
                rc.Finding(
                    "doc_number_drift",
                    "high",
                    "2 number(s) the documentation states about itself are wrong",
                    source="doc_drift_scanners",
                    count=2,
                    detail="mcp tool counts: doc says 11, tree has 9",
                )
            ]

        monkeypatch.setattr(rc, "_doc_number_drift", fake_drift)
        material = rc.collect(str(tmp_path))

        kinds = {f["kind"] for f in material["findings"]}
        assert "doc_number_drift" in kinds, (
            "the collector is wired into collect(); if this fails the class is "
            "unreachable no matter what the scanners find"
        )

    def test_the_real_collector_is_wired_and_callable(self):
        """The counterpart: the fake above proves the wiring, this proves the
        real one runs without raising on the live tree (its ANSWER may be
        empty, which is a fact about the tree, not about the collector)."""
        from pathlib import Path

        assert isinstance(repo_coherence._doc_number_drift(Path(_ROOT).resolve()), list)

    def test_every_scanner_the_collector_names_is_actually_called(self):
        """A scanner missing from the loop is a class this lens cannot see.

        `scan_table_count_columns` was absent from the list for its whole first
        release: the lens reported "no number drift" while a scanner it does not
        run held the answer. Asserting the returned LABELS rather than reading
        the source, so a scanner that is imported and never invoked still fails.
        """
        called: list[str] = []

        class _Recorder:
            def __getattr__(self, name):
                def _scan(*_args, **_kwargs):
                    called.append(name)
                    return []

                return _scan

        import sys

        original = sys.modules.get("doc_drift_scanners")
        sys.modules["doc_drift_scanners"] = _Recorder()
        try:
            from pathlib import Path

            repo_coherence._doc_number_drift(Path(_ROOT).resolve())
        finally:
            if original is not None:
                sys.modules["doc_drift_scanners"] = original
            else:  # pragma: no cover - the module is always importable here
                del sys.modules["doc_drift_scanners"]

        assert "scan_table_count_columns" in called, called
        assert {
            "scan_version_refs",
            "scan_mcp_tool_counts",
            "scan_closed_list_enums",
            "scan_test_counts",
            "scan_code_counts",
        } <= set(called), called


class TestAReportNobodyReadsIsWorseThanNone:
    """AC-6: bounded, ranked, and honest about its own blind spots."""

    def test_findings_are_ordered_most_severe_first(self, live):
        order = [repo_coherence.SEVERITY_ORDER.index(f["severity"]) for f in live["findings"]]
        assert order == sorted(order)

    def test_volume_is_capped_and_the_remainder_is_counted_not_dropped(self, monkeypatch, tmp_path):
        """Truncation must be VISIBLE — a silently shortened list is a lie about
        how much was found.

        Run against an EMPTY tree, so the only findings are the synthetic ones
        and the arithmetic is exact. Pointed at the live repository this counted
        the real findings too and the expected remainder became a moving number
        — a test whose expectation drifts with the tree tests nothing.
        """
        import repo_coherence as rc

        many = [
            rc.Finding(f"k{i}", "low", f"finding {i}", source="synthetic")
            for i in range(rc.MAX_FINDINGS + 7)
        ]
        monkeypatch.setattr(rc, "_orphans", lambda _root: many)
        material = rc.collect(str(tmp_path))

        assert len(material["findings"]) == rc.MAX_FINDINGS
        assert material["truncated"] == 7

    def test_the_report_states_what_it_did_not_examine(self, live):
        rendered = repo_coherence.render_markdown(live)
        assert "NOT examined by this lens" in rendered
        assert "runtime behaviour" in rendered

    def test_the_report_offers_candidates_not_filed_tasks(self, live):
        """AC-4. The lens proposes; filing stays a person's decision."""
        rendered = repo_coherence.render_markdown(live)
        assert "CANDIDATES" in rendered

    def test_an_empty_result_is_rendered_as_suspicious_not_as_success(self):
        """The failure mode from AC-5, in the output itself: a reader who gets
        an empty report must not read it as a clean bill of health."""
        rendered = repo_coherence.render_markdown(
            {
                "findings": [],
                "truncated": 0,
                "collectors_run": 8,
                "collectors_skipped": [],
                "not_examined": list(repo_coherence.NOT_EXAMINED),
            }
        )
        assert "SUSPICION" in rendered.upper()


class TestACollectorFailureIsNamedNeverSwallowed:
    def test_a_raising_collector_becomes_a_reported_gap(self, monkeypatch):
        import repo_coherence as rc

        def boom(_root):
            raise RuntimeError("collector exploded")

        monkeypatch.setattr(rc, "_orphans", boom)
        material = rc.collect(_ROOT)

        assert any("orphan_files" in s for s in material["collectors_skipped"]), (
            "a collector that died must appear as a named gap; dropping it "
            "silently would report a cleaner repository than was measured"
        )
        assert "collector exploded" in " ".join(material["collectors_skipped"])
