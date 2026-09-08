"""The graph answers navigation in twenty lines, or it is worse than a grep.

MEASURED BEFORE THIS EXISTED (session #236, live graph). An unranked neighbour
list is not an answer:

    scripts/verify_scope_honesty.py    42 neighbours, 2,881 KB
    scripts/gate_test_resolver.py      38 neighbours, 2,779 KB
    scripts/service_artifact_graph.py  29 neighbours, 2,612 KB

MEASURED AFTER: the same three questions answered in 927, 945 and 916 bytes —
about one three-thousandth of what reading the neighbours would cost.

The saving is in the RANKING, not in the graph existing. That is why these tests
are mostly about ordering, about the budget, and about the three ways an answer
can be silently wrong: an empty list for an unknown file, a missing reason, and
a truncation nobody mentioned.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import graph_navigation as nav  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]


def _graph(tmp_path: Path, edges: list[tuple[str, str, str, str, int]]) -> Path:
    """A project whose graph holds exactly `edges` (src, dst, relation, layer, n)."""
    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True)
    svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
    try:
        for src, dst, relation, layer, observations in edges:
            a = svc.be.artifact_upsert(src, "test" if "test" in src else "code", f"h{src}")
            b = svc.be.artifact_upsert(dst, "code", f"h{dst}")
            svc.be.artifact_edge_add(a, b, relation, layer, 1.0, observations=observations)
    finally:
        svc.be.close()
    return root


class TestTheAnswerIsRankedByProvenance:
    """AC2. What a RUN observed outranks what a person declared, which outranks
    what git noticed happening together — that is the order in which the three
    are likely to be about THIS change rather than some other one."""

    def test_observed_comes_before_declared_before_cochange(self):
        ranked = nav.rank(
            [
                ("a.py", "git_cochange", 9),
                ("b.py", "declared_relevant_files", 1),
                ("c.py", "observed_coverage", 1),
            ]
        )
        assert [entry[0] for entry in ranked] == ["c.py", "b.py", "a.py"]

    def test_within_a_layer_the_observation_count_decides(self):
        ranked = nav.rank(
            [
                ("weak.py", "observed_coverage", 2),
                ("strong.py", "observed_coverage", 30),
            ]
        )
        assert [entry[0] for entry in ranked] == ["strong.py", "weak.py"]

    def test_one_line_per_file_even_when_several_layers_agree(self):
        """Two lines about one file spend the reader's budget twice to say one
        thing, and the budget is the whole saving."""
        ranked = nav.rank(
            [
                ("same.py", "git_cochange", 12),
                ("same.py", "observed_coverage", 3),
            ]
        )
        assert len(ranked) == 1
        assert ranked[0][1] == "observed_coverage", "the weaker layer won"

    def test_an_unrecognised_layer_sorts_last_and_still_says_something(self):
        ranked = nav.rank([("x.py", "some_future_layer", 1), ("y.py", "git_cochange", 1)])
        assert [entry[0] for entry in ranked] == ["y.py", "x.py"]
        assert "provenance" in ranked[1][3]


class TestEveryLineSaysWhy:
    """AC3. A ranked list without reasons is indistinguishable from an arbitrary
    one, and the reader cannot stop early — which is where the saving comes from."""

    @pytest.mark.parametrize(
        "layer,needle",
        [
            pytest.param("observed_coverage", "test run reached", id="observed"),
            pytest.param("declared_relevant_files", "one task", id="declared"),
            pytest.param("git_cochange", "git history", id="cochange"),
            pytest.param("declared_crosscutting", "CROSSCUTTING_SCOPE", id="crosscutting"),
        ],
    )
    def test_the_reason_names_the_evidence(self, layer, needle):
        (_path, _layer, _n, reason) = nav.rank([("f.py", layer, 1)])[0]
        assert needle in reason


class TestTheBudgetIsRealAndTheCutIsNamed:
    """AC1. Completeness is the failure mode here, not the goal."""

    def test_an_answer_is_cut_and_says_how_much_was_left_out(self, tmp_path):
        edges = [
            (f"tests/test_{i}.py", "scripts/target.py", "covers", "observed_coverage", i + 1)
            for i in range(25)
        ]
        root = _graph(tmp_path, edges)
        out = nav.answer(str(root), "scripts/target.py", budget=5)
        assert out.count("\n  tests/") == 5
        assert "20 weaker link(s) not shown" in out

    def test_a_small_answer_carries_no_remainder_line(self, tmp_path):
        root = _graph(
            tmp_path,
            [("tests/test_a.py", "scripts/target.py", "covers", "observed_coverage", 1)],
        )
        out = nav.answer(str(root), "scripts/target.py")
        assert "not shown" not in out

    def test_the_answer_is_orders_of_magnitude_smaller_than_reading_the_files(self, tmp_path):
        """The measurement that justifies the whole task: 927 bytes against
        2,881 KB on the live tree. Here the same property on a fixture."""
        edges = [
            (f"tests/test_{i}.py", "scripts/target.py", "covers", "observed_coverage", 1)
            for i in range(40)
        ]
        root = _graph(tmp_path, edges)
        out = nav.answer(str(root), "scripts/target.py")
        assert len(out.encode("utf-8")) < 1200, "the answer grew with the graph"


class TestAbsenceIsVisibleRatherThanEmpty:
    """AC5, and the one that decides whether an agent is misled. An empty list
    reads as 'this file is related to nothing' — a confident wrong answer."""

    def test_an_unknown_path_says_unknown_and_names_the_fix(self, tmp_path):
        root = _graph(
            tmp_path,
            [("tests/test_a.py", "scripts/known.py", "covers", "observed_coverage", 1)],
        )
        out = nav.answer(str(root), "scripts/never_heard_of.py")
        assert "NOT in the graph" in out
        assert "not 'unrelated'" in out
        assert "graph build" in out

    def test_an_empty_graph_says_so_and_names_the_command(self, tmp_path):
        """AC8."""
        root = tmp_path / "bare"
        (root / ".tausik").mkdir(parents=True)
        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        svc.be.close()
        out = nav.answer(str(root), "scripts/anything.py")
        assert "graph is empty" in out
        assert "graph build" in out

    def test_a_known_file_with_no_edges_is_not_confused_with_an_unknown_one(self, tmp_path):
        root = _graph(
            tmp_path,
            [("tests/test_a.py", "scripts/known.py", "covers", "observed_coverage", 1)],
        )
        # `tests/test_a.py` is in the graph; asking `affects` about it finds no
        # `covers` edge pointing AT it.
        out = nav.answer(str(root), "tests/test_a.py", direction="affects")
        assert "NOT in the graph" not in out
        assert "not observed" in out.lower()

    def test_the_affects_answer_admits_what_it_cannot_see(self, tmp_path):
        """The subprocess blindness, said at the point of use rather than only
        in the docs: a test exercising code in a subprocess is invisible."""
        root = _graph(
            tmp_path,
            [("tests/test_a.py", "scripts/known.py", "covers", "observed_coverage", 1)],
        )
        out = nav.answer(str(root), "tests/test_a.py", direction="affects")
        assert "SUBPROCESS" in out or "subprocess" in out


class TestTheTwoQuestionsAreNotMirrorImages:
    """AC4. This graph has no direction of dependency and says so, so `read`
    unions both directions while `affects` uses the one relation that IS
    directional."""

    def test_read_finds_a_neighbour_stored_on_either_side(self, tmp_path):
        root = _graph(
            tmp_path,
            [("scripts/other.py", "scripts/target.py", "co_changes", "git_cochange", 4)],
        )
        # The edge points AT the target; asking one direction would miss it —
        # measured on the live tree as 2 neighbours found out of 42.
        out = nav.answer(str(root), "scripts/target.py")
        assert "scripts/other.py" in out

    def test_affects_uses_only_covers_and_ignores_symmetric_edges(self, tmp_path):
        root = _graph(
            tmp_path,
            [
                ("scripts/other.py", "scripts/target.py", "co_changes", "git_cochange", 9),
                ("tests/test_t.py", "scripts/target.py", "covers", "observed_coverage", 2),
            ],
        )
        out = nav.answer(str(root), "scripts/target.py", direction="affects")
        assert "tests/test_t.py" in out
        assert "scripts/other.py" not in out, (
            "a co-change edge cannot say which side follows which, so it must not "
            "answer 'what will break'"
        )

    def test_the_headings_differ_so_the_reader_knows_which_question_was_asked(self, tmp_path):
        root = _graph(
            tmp_path,
            [("tests/test_t.py", "scripts/target.py", "covers", "observed_coverage", 1)],
        )
        read = nav.answer(str(root), "scripts/target.py")
        affects = nav.answer(str(root), "scripts/target.py", direction="affects")
        assert "read these first" in read
        assert "turn these red" in affects


class TestAnUnreadableGraphDoesNotCrashTheAnswer:
    def test_a_corrupt_database_reports_emptiness_rather_than_raising(self, tmp_path):
        root = tmp_path / "broken"
        (root / ".tausik").mkdir(parents=True)
        (root / ".tausik" / "tausik.db").write_bytes(b"not a database")
        out = nav.answer(str(root), "scripts/anything.py")
        assert "graph is empty" in out
