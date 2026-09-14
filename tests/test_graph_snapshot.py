"""What CHANGED IN THE RELATIONS since the last release, and what did not.

WHY STRUCTURAL AND NOT TEXTUAL. "Requirement #12 is no longer covered by any
test" cannot be expressed by comparing texts, however carefully worded — it is a
statement about EDGES. The RENAR drift detectors compare wording; comparing
snapshots compares structure.

MEASURED BEFORE THE STORAGE WAS CHOSEN (session #237, live graph): 4,288
artifacts and 23,695 edges serialise to 2,103 KB as TSV — comparable to all of
`scripts/*.py` at 3,683 KB — and to 150 KB compressed. Snapshots are therefore
stored WHOLE and compressed, not as deltas: a delta chain needs every link
intact, and at 150 KB per release that fragility buys nothing. A live snapshot
of this repository came out at 154 KB, which is the measurement holding.

THE TEST THAT MATTERS MOST is the one about differing completeness. Two
snapshots taken when the graph held different layers differ by every edge of the
missing layer — 6,051 for `observed_coverage` here — and none of that is drift
in the code. A first report full of false "vanished coverage" is a report nobody
reads a second time.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import graph_snapshot as snap  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]


def _snapshot(edges, layers=None, artifacts=100):
    return {
        "edges": [list(e) for e in edges],
        "completeness": {
            "artifacts": artifacts,
            "layers": layers if layers is not None else {},
            "stale": None,
        },
    }


class TestDifferingCompletenessIsNamedBeforeAnyDifference:
    """AC3, and the one that decides whether the reports keep being read."""

    def test_a_layer_missing_from_one_side_is_called_out(self):
        before = _snapshot(
            [["t.py", "a.py", "covers", "observed_coverage", 1]],
            layers={"observed_coverage": 6051},
        )
        after = _snapshot([], layers={})
        result = snap.diff(before, after)

        assert result["warnings"], "the difference in what was INDEXED went unmentioned"
        warning = result["warnings"][0]
        assert "observed_coverage" in warning
        assert "ABSENT" in warning
        assert "not in the code" in warning

    def test_the_warning_is_rendered_before_the_differences(self):
        before = _snapshot(
            [["t.py", "a.py", "covers", "observed_coverage", 1]],
            layers={"observed_coverage": 1},
        )
        text = snap.render("a", "b", snap.diff(before, _snapshot([], layers={})))
        assert text.index("!") < text.index("vanished"), (
            "the reader meets the vanished list before being told why it is there"
        )

    def test_a_layer_new_on_the_later_side_is_also_called_out(self):
        """The mirror case: edges NEW TO THE INDEX are not edges new in the
        code, and reading them as growth is the same error with the sign
        flipped."""
        result = snap.diff(
            _snapshot([], layers={}),
            _snapshot(
                [["t.py", "a.py", "covers", "observed_coverage", 1]],
                layers={"observed_coverage": 6051},
            ),
        )
        assert any("ABSENT from the earlier" in w for w in result["warnings"])

    def test_a_large_size_difference_is_called_out(self):
        result = snap.diff(
            _snapshot([], layers={"git_cochange": 1}, artifacts=100),
            _snapshot([], layers={"git_cochange": 1}, artifacts=4000),
        )
        assert any("coverage of the tree" in w for w in result["warnings"])

    def test_matching_completeness_produces_no_warning(self):
        """PREMISE. A warning that always fires says nothing."""
        layers = {"git_cochange": 5}
        result = snap.diff(_snapshot([], layers=layers), _snapshot([], layers=layers))
        assert result["warnings"] == []


class TestTheDifferenceItself:
    """AC4."""

    def test_appeared_and_vanished_are_separate(self):
        before = _snapshot([["a.py", "b.py", "co_changes", "git_cochange", 1]])
        after = _snapshot([["c.py", "d.py", "co_changes", "git_cochange", 1]])
        result = snap.diff(before, after)
        assert result["appeared"] == [("c.py", "d.py", "co_changes", "git_cochange")]
        assert result["vanished"] == [("a.py", "b.py", "co_changes", "git_cochange")]

    def test_an_unchanged_relation_appears_in_neither(self):
        same = [["a.py", "b.py", "co_changes", "git_cochange", 1]]
        result = snap.diff(_snapshot(same), _snapshot(same))
        assert result["appeared"] == []
        assert result["vanished"] == []
        assert "identical" in snap.render("a", "b", result)

    def test_a_changed_observation_count_is_NOT_a_structural_change(self):
        """The edge is the same relation; only how often it was seen moved.
        Reporting that as drift would fill every report with noise from ordinary
        work."""
        before = _snapshot([["a.py", "b.py", "co_changes", "git_cochange", 2]])
        after = _snapshot([["a.py", "b.py", "co_changes", "git_cochange", 40]])
        result = snap.diff(before, after)
        assert result["appeared"] == []
        assert result["vanished"] == []

    def test_the_example_list_is_bounded_and_the_remainder_stated(self):
        after = _snapshot(
            [[f"a{i}.py", "b.py", "co_changes", "git_cochange", 1] for i in range(30)]
        )
        text = snap.render("a", "b", snap.diff(_snapshot([]), after))
        assert f"{30 - snap.EXAMPLES} more" in text


class TestStructureSaysWhatTextCannot:
    """AC5. The claim the whole task rests on, shown rather than asserted."""

    def test_a_requirement_losing_its_last_test_is_visible(self):
        before = _snapshot(
            [["tests/test_req12.py", "scripts/req12.py", "covers", "observed_coverage", 3]],
            layers={"observed_coverage": 1},
        )
        after = _snapshot([], layers={"observed_coverage": 0})
        result = snap.diff(before, after)
        assert result["vanished"] == [
            ("tests/test_req12.py", "scripts/req12.py", "covers", "observed_coverage")
        ]
        # And the layer is present on BOTH sides, so this is real drift rather
        # than an indexing difference — no warning should dilute it.
        assert result["warnings"] == []


class TestStorageIsWholeAndCompressed:
    """AC1. 2,103 KB raw against 150 KB compressed decided this, not taste."""

    def test_a_snapshot_round_trips(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        payload = _snapshot([["a.py", "b.py", "co_changes", "git_cochange", 1]])
        path = snap.snapshot_path(str(tmp_path), "v1.9.0")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wb") as fh:
            fh.write(json.dumps(payload).encode("utf-8"))

        loaded = snap.read(str(tmp_path), "v1.9.0")
        assert loaded is not None
        assert loaded["edges"] == payload["edges"]

    def test_the_file_is_actually_compressed(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        path, _edges, _size = snap.write(str(tmp_path), "empty")
        assert path.endswith(".json.gz")
        with open(path, "rb") as fh:
            assert fh.read(2) == b"\x1f\x8b", "not a gzip stream"

    @pytest.mark.parametrize(
        "label",
        [
            pytest.param("../../evil", id="traversal"),
            pytest.param("..", id="bare_parent"),
            pytest.param("/etc/passwd", id="absolute"),
            pytest.param("a/b/c", id="nested"),
        ],
    )
    def test_a_label_cannot_escape_the_snapshot_directory(self, tmp_path, label):
        """A label arrives from a command line, so the property to check is
        where the path RESOLVES — not what the name looks like.

        `../../evil` sanitises to `..-..-evil`, which contains dots and escapes
        nothing: asserting the absence of those characters failed on a SAFE name
        while proving nothing about an unsafe one. Check the fact, not the shape
        (decision #335).
        """
        expected_dir = Path(tmp_path, snap.SNAPSHOT_DIR).resolve()
        resolved = Path(snap.snapshot_path(str(tmp_path), label)).resolve()
        assert resolved.parent == expected_dir, f"{label!r} escaped to {resolved}"


class TestAMissingSnapshotIsNotAnEmptyDiff:
    """AC7. A snapshot that does not exist says nothing about the relations."""

    def test_reading_an_absent_label_returns_none(self, tmp_path):
        assert snap.read(str(tmp_path), "never-taken") is None

    def test_a_corrupt_snapshot_returns_none_rather_than_half_a_graph(self, tmp_path):
        path = snap.snapshot_path(str(tmp_path), "broken")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"not gzip at all")
        assert snap.read(str(tmp_path), "broken") is None


class TestAnUnreadableDatabaseYieldsAbsenceNotAnEmptyGraph:
    def test_collect_on_a_broken_database(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_bytes(b"not a database")
        collected = snap.collect(str(tmp_path))
        assert collected["edges"] == []
        assert collected["completeness"]["artifacts"] == 0

    @pytest.mark.parametrize("missing", ["db", "dir"])
    def test_collect_without_a_project(self, tmp_path, missing):
        if missing == "dir":
            root = tmp_path / "nowhere"
        else:
            root = tmp_path
            (tmp_path / ".tausik").mkdir()
        collected = snap.collect(str(root))
        assert collected["edges"] == []


class TestACommittedSnapshotIsStillReadable:
    """A snapshot that git normalised as TEXT is worse than a missing one.

    MEASURED (session #237, immediately after the first snapshot was committed):
    git announced "CRLF will be replaced by LF", and the committed object was
    157,749 bytes against 157,751 on disk — two bytes gone and the gzip CRC
    failing. The file looked saved and could not be read.

    Nothing would have reported it. Git considered the file stored, no test
    opened it, no gate looked at it — and a release baseline is needed exactly
    once, while assembling the release, which is the worst possible moment to
    discover it.

    So the guard is a TEST over the real files rather than a rule in
    `.gitattributes` alone: the rule protects the files it names, and the test
    protects the ones somebody adds next.
    """

    def _snapshots(self) -> list[Path]:
        directory = _REPO / snap.SNAPSHOT_DIR
        return sorted(directory.glob("*.json.gz")) if directory.is_dir() else []

    def test_every_stored_snapshot_decompresses(self):
        stored = self._snapshots()
        for path in stored:
            with gzip.open(path, "rb") as fh:
                payload = json.loads(fh.read().decode("utf-8"))
            assert isinstance(payload.get("edges"), list), f"{path.name} holds no edges"

    def test_the_guard_can_go_red(self, tmp_path):
        """The negative half. On a checkout with no snapshots the loop above is
        vacuous, so the ability to refuse is asserted on a deliberately broken
        stream — otherwise this class would pass while checking nothing."""
        broken = tmp_path / "broken.json.gz"
        broken.write_bytes(b"\x1f\x8b" + b"not really gzip")
        with pytest.raises((OSError, EOFError, gzip.BadGzipFile)):
            with gzip.open(broken, "rb") as fh:
                fh.read()

    def test_the_binary_rule_covers_the_snapshot_directory(self):
        """The rule and the test guard different things: the rule keeps git from
        touching these files, the test notices if it did anyway."""
        text = (_REPO / ".gitattributes").read_text(encoding="utf-8")
        assert "graph-snapshots" in text and "binary" in text
