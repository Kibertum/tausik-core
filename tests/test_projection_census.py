"""The projection's cost is measured, and the measurement refuted the story that asked for it.

WHAT THE STORY BELIEVED: soft-archiving old done tasks would cut a projection occupying 69%
of the tree. WHAT THE TREE SAYS: 3317 of 4832 tracked files (68.6% of paths, 47.1% of
bytes), of which archival could ever reach 917 files -- 19% of paths, not 69% -- and reaches
zero today, because `state_export` selects FROM tasks with no `archived_at` filter.

THE FACT THE GUESS WAS MISSING is the first test below: `.tausik/tausik.db` is GITIGNORED.
The Markdown tree is the only carrier of state between machines, so a row dropped from it is
a row a fresh clone never sees. That is why the answer for every kind is "stays".

NO RATCHET, DELIBERATELY. A threshold on the projection's share would be crossed by ordinary
work -- every closed task adds a file -- and a threshold ordinary work crosses gets switched
off, taking the measurement with it. The bound that does exist sits on per-entry journal
length, at the point of writing.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

from conftest import canonical_ddl

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from projection_census import (  # noqa: E402
    KINDS,
    census,
    reachable_shrink,
    render,
)


@pytest.fixture
def tree(tmp_path):
    """A git tree holding a projection, some code, and one archivable task."""
    subprocess.run(["git", "init", "-b", "main", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "tool.py").write_text("x = 1\n" * 50, encoding="utf-8")
    for kind, n, body in (("tasks", 3, "t" * 400), ("memory", 2, "m" * 100)):
        (tmp_path / "tausik" / kind).mkdir(parents=True)
        for i in range(n):
            (tmp_path / "tausik" / kind / f"{kind}-{i}.md").write_text(
                f"---\nslug: {kind}-{i}\n---\n\n## Goal\n\n{body}\n\n## Journal\n\n- entry\n",
                encoding="utf-8",
            )
    (tmp_path / "tausik" / "gates.json").write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


class TestTheCensusWeighsWhatIsThere:
    def test_the_projection_is_counted_against_the_whole_tracked_tree(self, tree):
        c = census(str(tree))
        assert c.files == 5, "3 tasks + 2 memory; the config JSON beside them is not projection"
        assert c.tracked_files == 7
        assert 0 < c.path_share < 100
        assert c.bytes_ < c.tracked_bytes

    def test_an_untracked_file_is_somebody_s_working_state_and_is_not_counted(self, tree):
        (tree / "tausik" / "tasks" / "not-added.md").write_text("x\n", encoding="utf-8")
        assert census(str(tree)).kinds[0].files == 3

    def test_journal_bytes_are_reported_apart_from_the_rest(self, tree):
        """A different question: the row count is what was DONE, the journal is how much was
        written about each closure — the one part a writing habit can move."""
        c = census(str(tree))
        assert 0 < c.journal_bytes < next(k for k in c.kinds if k.name == "tasks").bytes_

    def test_a_tracked_path_missing_from_the_checkout_is_zero_and_not_a_crash(self, tree):
        (tree / "scripts" / "tool.py").unlink()
        assert census(str(tree)).tracked_files == 7

    def test_outside_a_repository_the_answer_is_empty_rather_than_invented(self, tmp_path):
        c = census(str(tmp_path))
        assert c.tracked_files == 0 and c.files == 0
        assert c.path_share == 0.0 and c.byte_share == 0.0

    def test_every_declared_kind_is_a_real_subtree_of_this_project(self):
        sys.path.insert(0, str(_REPO / "scripts"))
        from publication_snapshot import EXCLUDED_FROM_PUBLIC_SNAPSHOT

        for kind in KINDS:
            path = _REPO / "tausik" / kind
            if not path.is_dir() and f"tausik/{kind}/" in EXCLUDED_FROM_PUBLIC_SNAPSHOT:
                continue  # the public snapshot leaves the projection out by design
            assert path.is_dir(), kind


class TestTheCeilingOnArchival:
    def test_only_done_rows_past_the_age_are_reachable(self, tree):
        conn = sqlite3.connect(":memory:")
        conn.executescript(canonical_ddl("tasks"))
        conn.executemany(
            "INSERT INTO tasks (slug, title, status, completed_at, created_at, updated_at) "
            "VALUES (?,?,?,?,'2020-01-01T00:00:00Z','2020-01-01T00:00:00Z')",
            [
                ("tasks-0", "t0", "done", "2020-01-01T00:00:00Z"),
                ("tasks-1", "t1", "done", None),
                ("tasks-2", "t2", "active", "2020-01-01T00:00:00Z"),
            ],
        )
        files, size = reachable_shrink(conn, str(tree))
        assert files == 1 and size > 0, "the old done row only"

    def test_a_row_with_no_file_does_not_inflate_the_ceiling(self, tree):
        conn = sqlite3.connect(":memory:")
        conn.executescript(canonical_ddl("tasks"))
        conn.execute(
            "INSERT INTO tasks (slug, title, status, completed_at, created_at, updated_at) VALUES "
            "('never-projected','n','done','2020-01-01T00:00:00Z','2020-01-01T00:00:00Z','2020-01-01T00:00:00Z')"
        )
        assert reachable_shrink(conn, str(tree)) == (0, 0)


class TestTheTreeIsTheOnlyCarrier:
    """THE FACT THE STORY WAS MISSING, and the reason every kind's answer is "stays"."""

    def test_the_database_does_not_travel(self):
        listed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".tausik/tausik.db"],
            cwd=_REPO,
            capture_output=True,
            check=False,
        )
        assert listed.returncode != 0, (
            "if the DB were ever tracked, dropping rows from the projection would stop "
            "losing them on a fresh clone and this whole decision would need retaking"
        )

    def test_the_exporter_still_has_no_archived_at_filter_on_tasks(self):
        """Pinned because the story assumed the opposite. If a filter is ever added, the
        round-trip negative in this task's acceptance criteria becomes mandatory."""
        text = (_REPO / "scripts" / "state_export.py").read_text(encoding="utf-8")
        assert "FROM memory WHERE archived_at IS NULL" in text, "memory does filter"
        assert "FROM tasks WHERE archived_at IS NULL" not in text, "tasks deliberately do not"


class TestTheReportAnswersBeforeItExplains:
    def test_the_first_line_is_the_number_somebody_asked_for(self, tree):
        first = render(census(str(tree))).splitlines()[0]
        assert "State projection:" in first and "% of paths" in first

    def test_the_ceiling_is_printed_with_why_it_is_not_taken(self, tree):
        conn = sqlite3.connect(":memory:")
        conn.executescript(canonical_ddl("tasks"))
        conn.execute(
            "INSERT INTO tasks (slug, title, status, completed_at, created_at, updated_at) VALUES "
            "('tasks-0','t0','done','2020-01-01T00:00:00Z','2020-01-01T00:00:00Z','2020-01-01T00:00:00Z')"
        )
        text = render(census(str(tree)), reachable_shrink(conn, str(tree)))
        assert "gitignored" in text and "only carrier" in text

    def test_an_empty_projection_prints_shares_rather_than_dividing_by_zero(self, tmp_path):
        assert "0 of 0" in render(census(str(tmp_path)))


class TestTheDecisionIsWrittenDownWhereItIsRead:
    @pytest.mark.parametrize("lang", ["en", "ru"])
    def test_every_kind_gets_a_verdict_in_the_cost_document(self, lang):
        """A census with no verdict is a number the next person re-argues from scratch."""
        text = (_REPO / "docs" / lang / "state-projection-cost.md").read_text(encoding="utf-8")
        for kind in KINDS:
            assert kind in text, f"{lang}: {kind} has no verdict"
