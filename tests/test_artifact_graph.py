"""The artifact graph: what it may store, and what it must admit it cannot vouch for.

Two properties carry this feature, and they are the two that make a graph
trustworthy rather than merely populated:

  1. NO EDGE WITHOUT PROVENANCE. "co-changed in twelve commits" and "declared in
     relevant_files" are different claims. An edge that cannot say which it is
     turns a guess into a fact — the failure this release has been removing
     everywhere else — so the schema refuses to store one.
  2. NO SILENT ANSWER OVER STALE ROWS. A graph 90% fresh is useful if it names
     the other 10%; one global timestamp is useless from the first edit. A stale
     answer that looks fresh is the worst outcome available, because it is
     indistinguishable from a correct one.

Everything else here exists to keep those two honest.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from backend_schema_graph import ARTIFACT_KINDS  # noqa: E402
from service_artifact_graph import classify, fingerprint  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "graph.db")))
    yield s
    s.be.close()


@pytest.fixture
def tree(tmp_path):
    """A small working tree the graph can be pointed at."""
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "scripts" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (root / "scripts" / "other.py").write_text("y = 2\n", encoding="utf-8")
    (root / "docs.md").write_text("# doc\n", encoding="utf-8")
    return root


class TestAnEdgeCannotBeStoredWithoutSayingWhereItCameFrom:
    def test_the_layer_is_a_closed_list_the_database_enforces(self, svc, tree):
        src = svc.be.artifact_upsert("scripts/mod.py", "code", "h1")
        dst = svc.be.artifact_upsert("scripts/other.py", "code", "h2")

        with pytest.raises(sqlite3.IntegrityError):
            svc.be.artifact_edge_add(src, dst, "co_changes", "rumour", 0.5)

        # PREMISE: a real layer on the same pair goes in, so the refusal above
        # is about the layer and not about the pair.
        assert svc.be.artifact_edge_add(src, dst, "co_changes", "git_cochange", 0.5) > 0

    def test_the_same_pair_may_carry_an_inference_and_a_declaration_at_once(self, svc):
        """They are two claims. Collapsing them would erase the distinction the
        table exists to keep — so the identity of an edge includes its layer."""
        src = svc.be.artifact_upsert("scripts/mod.py", "code", "h1")
        dst = svc.be.artifact_upsert("scripts/other.py", "code", "h2")

        svc.be.artifact_edge_add(src, dst, "co_changes", "git_cochange", 0.6, observations=4)
        svc.be.artifact_edge_add(src, dst, "references", "declared_relevant_files", 1.0)

        layers = {e["layer"] for e in svc.be.edges_from_artifact(src)}
        assert layers == {"git_cochange", "declared_relevant_files"}

    def test_re_observing_updates_strength_instead_of_duplicating(self, svc):
        src = svc.be.artifact_upsert("a.py", "code", "h1")
        dst = svc.be.artifact_upsert("b.py", "code", "h2")
        svc.be.artifact_edge_add(src, dst, "co_changes", "git_cochange", 0.4, observations=2)
        svc.be.artifact_edge_add(src, dst, "co_changes", "git_cochange", 0.8, observations=9)

        edges = svc.be.edges_from_artifact(src)
        assert len(edges) == 1
        assert (edges[0]["confidence"], edges[0]["observations"]) == (0.8, 9)


class TestFreshnessIsPerArtifact:
    def test_an_edited_file_is_named_and_the_others_are_not(self, svc, tree):
        svc.graph_index_paths(["scripts/mod.py", "scripts/other.py"], root=str(tree))
        assert svc.graph_stale_artifacts(root=str(tree)) == []

        (tree / "scripts" / "mod.py").write_text("x = 999\n", encoding="utf-8")

        stale = svc.graph_stale_artifacts(root=str(tree))
        assert [s["path"] for s in stale] == ["scripts/mod.py"], (
            "staleness must be per artifact — the untouched file is still described correctly"
        )

    def test_a_deleted_file_reads_as_changed_rather_than_raising(self, svc, tree):
        svc.graph_index_paths(["scripts/mod.py"], root=str(tree))
        (tree / "scripts" / "mod.py").unlink()

        assert [s["path"] for s in svc.graph_stale_artifacts(root=str(tree))] == ["scripts/mod.py"]


class TestAnAnswerNeverHidesThatItIsStale:
    """THE NEGATIVE SCENARIO, and the reason the flag is computed per query."""

    def test_an_answer_touching_an_edited_neighbour_says_so_and_names_it(self, svc, tree):
        svc.graph_index_paths(["scripts/mod.py", "scripts/other.py", "docs.md"], root=str(tree))
        src = svc.be.artifact_get("scripts/mod.py")["id"]
        dst = svc.be.artifact_get("scripts/other.py")["id"]
        svc.be.artifact_edge_add(src, dst, "co_changes", "git_cochange", 0.7, observations=5)

        fresh = svc.neighbours_of("scripts/mod.py", root=str(tree))
        # PREMISE: the same query is clean before the edit, so the flag below is
        # caused by the edit and not by the query always saying so.
        assert fresh["partially_stale"] is False
        assert fresh["stale"] == []

        (tree / "scripts" / "other.py").write_text("y = 3\n", encoding="utf-8")

        answer = svc.neighbours_of("scripts/mod.py", root=str(tree))
        assert answer["partially_stale"] is True, (
            "an answer resting on an artifact the graph no longer describes must say so"
        )
        assert answer["stale"] == ["scripts/other.py"], "and must name which one"
        # The edges are still returned: a partially stale answer is useful, a
        # silent one is not, and refusing to answer would be its own dishonesty.
        assert [e["target"] for e in answer["edges"]] == ["scripts/other.py"]

    def test_an_unknown_path_is_reported_as_unknown_not_as_empty(self, svc, tree):
        answer = svc.neighbours_of("scripts/never_indexed.py", root=str(tree))
        assert answer["known"] is False
        assert answer["edges"] == []

    def test_every_returned_edge_carries_its_layer_and_confidence(self, svc, tree):
        svc.graph_index_paths(["scripts/mod.py", "docs.md"], root=str(tree))
        src = svc.be.artifact_get("scripts/mod.py")["id"]
        dst = svc.be.artifact_get("docs.md")["id"]
        svc.be.artifact_edge_add(
            src, dst, "documents", "declared_crosscutting", 1.0, source_ref="tests/test_x.py"
        )

        edge = svc.neighbours_of("scripts/mod.py", root=str(tree))["edges"][0]
        assert edge["layer"] == "declared_crosscutting"
        assert edge["confidence"] == 1.0
        assert edge["source_ref"] == "tests/test_x.py"


class TestLayerZeroReadsHistoryAndLayerOneReadsDeclarations:
    @staticmethod
    def _git_repo(root):
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@e",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@e",
        }
        subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=env)
        for i in range(3):
            (root / "scripts" / "mod.py").write_text(f"x = {i}\n", encoding="utf-8")
            (root / "scripts" / "other.py").write_text(f"y = {i}\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root, check=True, env=env)
            subprocess.run(["git", "commit", "-q", "-m", f"c{i}"], cwd=root, check=True, env=env)
        return env

    def test_cochange_confidence_grows_with_observations_and_never_reaches_certainty(
        self, svc, tree
    ):
        self._git_repo(tree)
        written = svc.graph_build_cochange(root=str(tree), window=50, min_shared=2)
        assert written >= 1

        edges = svc.be.edges_from_artifact(svc.be.artifact_get("scripts/mod.py")["id"])
        edge = next(e for e in edges if e["layer"] == "git_cochange")
        assert edge["observations"] >= 2
        assert 0 < edge["confidence"] < 1.0, (
            "co-change is an observation; no number of them makes it a declaration"
        )

    def test_a_declared_scope_is_read_rather_than_asked_for_again(self, svc, tree):
        (tree / "tests" / "test_thing.py").write_text(
            'CROSSCUTTING_SCOPE = ["scripts/mod.py"]\n', encoding="utf-8"
        )
        written = svc.graph_build_declared(root=str(tree))
        assert written >= 1

        src = svc.be.artifact_get("tests/test_thing.py")
        edges = svc.be.edges_from_artifact(int(src["id"]))
        assert [(e["target_path"], e["layer"], e["confidence"]) for e in edges] == [
            ("scripts/mod.py", "declared_crosscutting", 1.0)
        ]

    def test_a_declared_directory_prefix_makes_no_edge(self, svc, tree):
        """A declaration may name a directory. Expanding it would claim relations
        to files nobody named — an invented fact, which is what this refuses."""
        (tree / "tests" / "test_dir.py").write_text(
            'CROSSCUTTING_SCOPE = [".github/workflows/"]\n', encoding="utf-8"
        )
        svc.graph_build_declared(root=str(tree))

        src = svc.be.artifact_get("tests/test_dir.py")
        assert svc.be.edges_from_artifact(int(src["id"])) == []


class TestTheSmallHelpers:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("scripts/mod.py", "code"),
            ("tests/test_mod.py", "test"),
            ("docs/en/guide.md", "doc"),
            (".github/workflows/tests.yml", "config"),
            ("assets/logo.png", "other"),
        ],
    )
    def test_kind_is_decided_by_location_then_suffix(self, path, expected):
        kind = classify(path)
        assert kind == expected
        # And it can never invent a kind the table would refuse: the column has
        # a CHECK over this exact list, so a classifier returning anything else
        # would turn a mislabelled file into a failed INSERT at index time.
        assert kind in ARTIFACT_KINDS

    def test_the_fingerprint_is_the_existing_hash_not_a_second_one(self, tree):
        """Reusing `compute_files_hash` is the point: one answer to "did this
        file change", with the measurements already behind it."""
        before = fingerprint("scripts/mod.py", str(tree))
        (tree / "scripts" / "mod.py").write_text("x = 42\n", encoding="utf-8")
        assert fingerprint("scripts/mod.py", str(tree)) != before
