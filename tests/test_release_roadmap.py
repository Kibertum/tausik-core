"""ROADMAP.md: derived from the record, and unable to rot unnoticed.

Two families here. The first builds tiny databases and holds the DERIVATION to
its rules — whose declaration the composition follows, what counts as a
declaration at all, and what happens when there is none. The second reads the
LIVE database and the committed file and asks whether the published map still
says what the project says, which is the failure the predecessor PDF had: it
was true on the day it was built and nothing ever noticed it stop being true.

The negative for the freshness guard edits a digit into a copy of the committed
map, because a guard that only ever sees matching inputs has never shown it can
say no.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from conftest import DORMANT_WITHOUT_LIVE_DB, canonical_schema_db  # noqa: E402

import release_roadmap  # noqa: E402
import release_roadmap_composition  # noqa: E402
from release_roadmap import (  # noqa: E402
    OUTPUT_FILENAME,
    PDF_SNAPSHOT_DATE,
    RoadmapUnreadable,
    composition,
    render,
    run_main,
)

# Reads the committed map, the live DB and .gitignore — no import edge selects
# this module, so the scoped gate is told where its subject lives. LITERALS on
# purpose: the resolver reads this with `ast.literal_eval` and never imports the
# module, so a name here reads as "declared nothing" and the whole file goes
# invisible to every scoped run. `test_the_declaration_names_the_artifact`
# checks the literal against the generator's own constant.
CROSSCUTTING_SCOPE = ["scripts/", "ROADMAP.md", ".gitignore"]

COMMITTED = os.path.join(_ROOT, OUTPUT_FILENAME)
PROJECT_DB = os.path.join(_ROOT, ".tausik", "tausik.db")
PDF = "TAUSIK-roadmap.pdf"

_TS = "2026-01-01T00:00:00Z"


def _db(stories=("alpha-story", "beta-story", "gamma-story")):
    """A canonical-schema DB with one epic and the named stories."""
    conn = canonical_schema_db()
    conn.execute(
        "INSERT INTO epics (slug, title, status, created_at) VALUES (?,?,?,?)",
        ("an-epic", "An epic", "active", _TS),
    )
    epic_id = conn.execute("SELECT id FROM epics").fetchone()[0]
    for slug in stories:
        conn.execute(
            "INSERT INTO stories (epic_id, slug, title, status, created_at) VALUES (?,?,?,?,?)",
            (epic_id, slug, f"Title of {slug}", "active", _TS),
        )
    return conn


def _decide(conn, text, created_at=_TS):
    conn.execute("INSERT INTO decisions (decision, created_at) VALUES (?,?)", (text, created_at))


def _task(conn, story_slug, status):
    story_id = conn.execute("SELECT id FROM stories WHERE slug=?", (story_slug,)).fetchone()[0]
    n = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    conn.execute(
        "INSERT INTO tasks (story_id, slug, title, status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?)",
        (story_id, f"t{n}", f"Task {n}", status, _TS, _TS),
    )


class TestCompositionIsRead:
    """Which stories are in the release is the owner's call, taken from the record."""

    def test_the_newest_declaration_is_the_one_in_force(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9 = 1: alpha-story и beta-story")
        _decide(conn, "ОБЪЁМ 9.9 = 2: beta-story и gamma-story")
        comp = composition(conn)
        assert [s["slug"] for s in comp["stories"]] == ["beta-story", "gamma-story"], (
            "an earlier declaration overrode a later one — scope is restated "
            "every shift and the last statement is what holds"
        )

    def test_one_story_named_is_a_decision_about_that_story_not_about_scope(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9 = 2: alpha-story и beta-story")
        _decide(conn, "gamma-story отложена: премиса не подтвердилась")
        comp = composition(conn)
        assert [s["slug"] for s in comp["stories"]] == ["alpha-story", "beta-story"], (
            "an ordinary per-story decision was mistaken for a scope declaration"
        )

    def test_no_declaration_at_all_refuses_instead_of_publishing_an_empty_release(self):
        conn = _db()
        _decide(conn, "Ничего про истории здесь не сказано")
        with pytest.raises(RoadmapUnreadable) as err:
            composition(conn)
        assert "undeclared" in str(err.value)

    def test_the_order_is_the_owner_s_not_the_alphabet_s(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: gamma-story 3, alpha-story 1")
        comp = composition(conn)
        assert [s["slug"] for s in comp["stories"]] == ["gamma-story", "alpha-story"], (
            "re-sorting substitutes my ordering for the owner's in a document "
            "whose subject is their plan"
        )

    def test_the_version_label_comes_from_the_declaration(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9 = 2: alpha-story и beta-story")
        assert composition(conn)["version"] == "9.9"


class TestCharterIsFollowed:
    """Why the release is what it is: a reference read out of the first declaration."""

    def test_the_first_declaration_points_at_the_charter_by_number(self):
        conn = _db()
        _decide(conn, "ЯДРО ДОКАЗАТЕЛЬСТВА, а не партия дефектов")  # id 1
        _decide(conn, "ОБЪЁМ 9.9 СТРОГО ПО #1: alpha-story, beta-story")  # id 2
        _decide(conn, "ОБЪЁМ 9.9 = 2: alpha-story, beta-story")  # id 3
        charter = composition(conn)["charter"]
        assert charter["id"] == 1, "the charter must be followed, not assumed"

    def test_a_reference_to_nothing_falls_back_to_the_declaration_itself(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9 СТРОГО ПО #999: alpha-story, beta-story")
        charter = composition(conn)["charter"]
        assert charter["id"] == 1, "a dangling reference must not become an invented citation"

    def test_a_decision_citing_its_own_number_is_not_its_own_charter(self):
        """Self-citation is a formatting artefact, not a link to a predecessor."""
        _skip = "ЯДРО: не партия дефектов"
        conn = _db()
        _decide(conn, _skip)  # id 1 — the real charter
        _decide(conn, "ПОПРАВКА К #2, ПО #1: alpha-story, beta-story")  # id 2
        charter = composition(conn)["charter"]
        assert charter["id"] == 1, (
            "the finder stopped at the decision's own number and never reached "
            "the reference that points outward"
        )

    def test_the_charter_section_says_so_when_no_reference_resolves(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        text = render(conn)
        assert "#1" in text  # the declaration itself stands in as the charter
        assert "Вопрос версии" in text


class TestCountsAreCounted:
    def test_everything_that_is_not_done_is_still_owed(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        for status in ("planning", "active", "blocked", "review", "done"):
            _task(conn, "alpha-story", status)
        text = render(conn)
        row = [ln for ln in text.splitlines() if ln.startswith("| `alpha-story`")][0]
        assert "| 4 | 1 |" in row, f"remaining/done miscounted: {row}"

    def test_the_total_is_the_sum_over_the_release_stories_only(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        _task(conn, "alpha-story", "planning")
        _task(conn, "beta-story", "planning")
        _task(conn, "gamma-story", "planning")  # outside the declaration
        text = render(conn)
        assert "| **Итого** | | **2** |" in text

    def test_stories_the_declaration_omits_are_shown_as_outside_it(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        text = render(conn)
        outside = text.split("## Что в релиз НЕ входит", 1)[1]
        assert "`gamma-story`" in outside
        assert "`alpha-story`" not in outside


class TestDeclaredCompositionIsRead:
    """The live defect: decision #363 answered three owner questions, happened to
    mention three story slugs, and the inference read it as a full restatement —
    the map shrank from thirteen stories to three while quoting #360, which
    names ten of them, as the charter. A declaration is READ from a line written
    as one; prose that mentions two slugs no longer restates the release."""

    def test_a_later_mention_does_not_displace_a_declared_composition(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9. Состав: alpha-story, beta-story")
        _decide(conn, "Три ответа владельца: beta-story остаётся, gamma-story — 9.9 тоже")
        comp = composition(conn)
        assert [s["slug"] for s in comp["stories"]] == ["alpha-story", "beta-story"], (
            "a decision that merely mentions two stories overrode the declared "
            "composition — the exact reading that shrank 1.9 to three stories"
        )
        assert comp["declared"] is True
        assert comp["basis"]["id"] == 1

    def test_the_newest_declaration_wins_and_keeps_the_owner_s_order(self):
        conn = _db()
        _decide(conn, "Состав: alpha-story, beta-story")
        _decide(conn, "Пересмотр. Состав: gamma-story, alpha-story")
        assert [s["slug"] for s in composition(conn)["stories"]] == [
            "gamma-story",
            "alpha-story",
        ]

    def test_the_english_spelling_of_the_line_is_the_same_line(self):
        conn = _db()
        _decide(conn, "Scope 9.9. Composition: `beta-story`, `gamma-story`")
        assert [s["slug"] for s in composition(conn)["stories"]] == ["beta-story", "gamma-story"]

    def test_the_list_ends_at_the_sentence_and_prose_inside_it_is_loud(self):
        conn = _db()
        _decide(conn, "Состав: alpha-story, beta-story. Впредь состав меняется только строкой.")
        assert [s["slug"] for s in composition(conn)["stories"]] == ["alpha-story", "beta-story"]
        _decide(conn, "Состав: alpha-story, beta-story и gamma-story")
        with pytest.raises(RoadmapUnreadable) as err:
            composition(conn)
        assert "beta-story и gamma-story" in str(err.value), (
            "prose inside the list must surface as an unknown slug, not as a shorter release"
        )

    def test_an_unknown_slug_on_the_line_is_refused_by_name(self):
        conn = _db()
        _decide(conn, "Состав: alpha-story, delta-story")
        with pytest.raises(RoadmapUnreadable) as err:
            composition(conn)
        assert "delta-story" in str(err.value), (
            "a typo would otherwise drop a story from the release silently"
        )

    def test_an_empty_line_is_a_refusal_not_an_empty_release(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")  # the inference would read this
        _decide(conn, "Состав:   ")
        with pytest.raises(RoadmapUnreadable) as err:
            composition(conn)
        assert "empty" in str(err.value)

    def test_the_named_charter_is_followed(self):
        conn = _db()
        _decide(conn, "ЯДРО: два обещания, а не партия дефектов")  # id 1
        _decide(conn, "ОБЪЁМ по #1: alpha-story, beta-story")  # id 2 — the chain would pick this
        _decide(conn, "Пересказ. Устав: #1. Состав: alpha-story, beta-story, gamma-story")
        assert composition(conn)["charter"]["id"] == 1

    def test_the_named_charter_wins_where_the_chain_would_disagree(self):
        conn = _db()
        _decide(conn, "ЯДРО первое")  # id 1
        _decide(conn, "ЯДРО второе, переопределяет #1")  # id 2
        _decide(conn, "ОБЪЁМ по #1: alpha-story, beta-story")  # id 3 — the chain lands on 1
        _decide(conn, "Устав: #2. Состав: alpha-story, beta-story")  # id 4
        assert composition(conn)["charter"]["id"] == 2, (
            "the explicit charter reference lost to the chain walk"
        )

    def test_the_line_is_read_in_any_case_and_a_repeat_is_refused(self):
        conn = _db()
        _decide(conn, "состав: alpha-story, beta-story")
        _decide(conn, "Про beta-story и gamma-story: два упоминания, не объявление")
        assert [s["slug"] for s in composition(conn)["stories"]] == ["alpha-story", "beta-story"], (
            "a lowercase line fell through to the inference — the defect class, reopened"
        )
        _decide(conn, "Состав: alpha-story, beta-story, alpha-story")
        with pytest.raises(RoadmapUnreadable) as err:
            composition(conn)
        assert "alpha-story" in str(err.value) and "more than once" in str(err.value)

    def test_one_declared_story_is_a_release_of_one_story(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        _decide(conn, "Сужение. Состав: gamma-story")
        assert [s["slug"] for s in composition(conn)["stories"]] == ["gamma-story"]

    def test_a_dangling_charter_falls_back_to_the_chain(self):
        conn = _db()
        _decide(conn, "ЯДРО")  # id 1
        _decide(conn, "ОБЪЁМ по #1: alpha-story, beta-story")  # id 2 cites 1
        _decide(conn, "Устав: #999. Состав: alpha-story, beta-story")  # id 3
        assert composition(conn)["charter"]["id"] == 1, (
            "a reference to nothing must fall back to the record, not to an invented decision"
        )

    def test_a_journal_without_the_line_is_read_as_before_and_says_so(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9 = 2: alpha-story и beta-story")
        comp = composition(conn)
        assert comp["declared"] is False
        text = render(conn)
        assert "вывод из прозы" in text
        assert "ОБЪЯВИВШЕГО" not in text

    def test_the_map_names_the_declaration_as_its_source(self):
        conn = _db()
        _decide(conn, "Состав: alpha-story, beta-story")
        text = render(conn)
        assert "ОБЪЯВИВШЕГО его строкой «Состав:»" in text
        assert "вывод из прозы" not in text


class TestOutsideTheReleaseOpenIsApartFromDone:
    """One table called a closed story 'not in this version'. Its work IS in the
    release tree; it is only not part of the promise. The deferred cost is the
    open stories alone, so the two are shown apart."""

    def test_an_open_story_carries_its_remainder_and_a_done_one_carries_none(self):
        conn = _db(stories=("alpha-story", "beta-story", "gamma-story", "delta-story"))
        conn.execute("UPDATE stories SET status='done' WHERE slug='delta-story'")
        _decide(conn, "Состав: alpha-story")
        _decide(conn, "Состав: alpha-story, beta-story")
        _task(conn, "gamma-story", "planning")
        _task(conn, "delta-story", "done")
        _task(conn, "delta-story", "done")
        text = render(conn)
        outside = text.split("## Что в релиз НЕ входит", 1)[1].split("## Траектория", 1)[0]
        open_part, done_part = outside.split("**Закрытые, составом не названные.**", 1)
        assert "| `gamma-story` | active | 1 |" in open_part
        assert "delta-story" not in open_part, "a closed story was listed as deferred cost"
        assert "| `delta-story` | 2 |" in done_part
        assert "не в этой версии" not in done_part

    def test_no_open_story_outside_is_said_rather_than_left_blank(self):
        conn = _db()
        conn.execute("UPDATE stories SET status='done' WHERE slug='gamma-story'")
        _decide(conn, "Состав: alpha-story, beta-story")
        text = render(conn)
        assert "Открытых историй вне состава нет." in text
        assert "`gamma-story`" in text


class TestTheMapMovesWithTheReleaseAndNotWithTheMinute:
    """The property the whole artifact rests on, in both directions.

    A map that changes when nothing about the release changed reddens the
    freshness guard on a file nobody touched — that happened three times in one
    shift, because the table printed a per-status breakdown and `active 1`
    appeared the moment any task was started. A map that does NOT change when
    the release does would be the worse failure, so both halves are pinned here.
    """

    @staticmethod
    def _one_task_db():
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        _task(conn, "alpha-story", "planning")
        return conn

    @staticmethod
    def _set_status(conn, status):
        conn.execute("UPDATE tasks SET status=?", (status,))

    def test_starting_a_task_does_not_move_the_map(self):
        conn = self._one_task_db()
        before = render(conn)
        self._set_status(conn, "active")
        assert render(conn) == before, (
            "opening a task changed the published map — the guard will report a "
            "stale file that nobody edited"
        )

    def test_closing_a_task_does_move_the_map(self):
        """The medicine must not cure the guard along with the churn."""
        conn = self._one_task_db()
        before = render(conn)
        self._set_status(conn, "done")
        assert render(conn) != before

    def test_being_stuck_is_still_published(self):
        """Blocked is a fact about the plan, and it cost the breakdown column."""
        conn = self._one_task_db()
        self._set_status(conn, "blocked")
        row = [ln for ln in render(conn).splitlines() if ln.startswith("| `alpha-story`")][0]
        assert "| 1 | 1 | 0 |" in row, f"blocked count missing: {row}"


class TestTrajectory:
    def test_no_recorded_points_is_not_zero_points(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        assert "не записало" in render(conn)

    def test_recorded_points_are_reproduced_and_compared_to_the_live_count(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story. Точки: 5, 4, 3.")
        _task(conn, "alpha-story", "planning")
        text = render(conn)
        assert "5 → 4 → 3" in text
        assert "Объявлено там же: 3. В живой базе сейчас: 1." in text
        assert "старше" in text, "a divergence must be explained, not just printed"

    def test_agreement_is_said_as_agreement(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story. Точки: 5, 1.")
        _task(conn, "alpha-story", "planning")
        text = render(conn)
        assert "подтверждает" in text


class TestTheMapItself:
    def test_rendering_twice_gives_the_same_bytes(self):
        """No clock in the output — a timestamp would make freshness unprovable."""
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        assert render(conn) == render(conn)

    def test_the_snapshot_is_named_kept_and_left_out_of_git(self):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        text = render(conn)
        assert PDF in text and PDF_SNAPSHOT_DATE in text
        assert "НЕ переиздаётся и НЕ удаляется" in text
        assert ".gitignore" in text

    def test_the_withdrawn_version_question_is_only_ever_named_as_withdrawn(self):
        """It may appear as history. It may not appear as the question of the version."""
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        text = render(conn)
        before_snapshot = text.split(f"## {PDF}", 1)[0]
        assert "Работает ли у чужих" not in before_snapshot


class TestWriteAndCheck:
    def test_check_on_a_missing_file_names_the_reissue_command(self, tmp_path, capsys):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        assert run_main(conn, str(tmp_path), check=True) == 1
        assert "tausik doc roadmap" in capsys.readouterr().out

    def test_write_then_check_is_green(self, tmp_path):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        assert run_main(conn, str(tmp_path)) == 0
        assert run_main(conn, str(tmp_path), check=True) == 0

    def test_a_digit_edited_into_the_written_map_is_caught(self, tmp_path, capsys):
        conn = _db()
        _decide(conn, "ОБЪЁМ 9.9: alpha-story, beta-story")
        _task(conn, "alpha-story", "planning")
        run_main(conn, str(tmp_path))
        path = tmp_path / OUTPUT_FILENAME
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("**1**", "**7**"), encoding="utf-8")
        assert run_main(conn, str(tmp_path), check=True) == 1
        assert "stale" in capsys.readouterr().out


@pytest.mark.skipif(not os.path.isfile(PROJECT_DB), reason=DORMANT_WITHOUT_LIVE_DB)
class TestCommittedMapIsCurrent:
    """The control the PDF never had: does the published map still match the project?"""

    @staticmethod
    def _live():
        import sqlite3

        return sqlite3.connect(f"file:{PROJECT_DB}?mode=ro", uri=True)

    def test_the_committed_map_exists_at_the_root(self):
        assert os.path.isfile(COMMITTED), (
            "the live roadmap is missing — reissue: tausik doc roadmap"
        )

    def test_the_committed_map_is_not_stale(self):
        conn = self._live()
        try:
            fresh = render(conn)
        finally:
            conn.close()
        with open(COMMITTED, encoding="utf-8", newline="") as fh:
            committed = fh.read()
        assert committed == fresh, (
            f"{OUTPUT_FILENAME} no longer matches the live database. Reissue: "
            "`tausik doc roadmap` (closing a task moves these counters, so the "
            "reissue belongs after `task done` and before the commit)."
        )

    def test_the_map_is_pinned_to_lf_so_a_checkout_is_not_a_rewrite(self):
        """Byte comparison + `core.autocrlf=true` = a false red in every clone.

        The map is written with LF and read back raw. Windows checks out CRLF by
        default, which would make the freshness guard report a stale map on a
        file nobody touched. The two derived trees carry the same pin.
        """
        out = subprocess.run(
            ["git", "check-attr", "eol", OUTPUT_FILENAME],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        assert out.stdout.strip().endswith(": eol: lf"), (
            f"{OUTPUT_FILENAME} is not pinned to LF in .gitattributes; the "
            f"freshness guard would go red on every Windows clone: {out.stdout}"
        )

    def test_the_snapshot_stays_out_of_git(self):
        """AC-3's other half: the PDF is kept, and kept UNTRACKED, by a rule."""
        out = subprocess.run(
            ["git", "check-ignore", "-v", PDF],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        assert out.returncode == 0 and ".gitignore" in out.stdout, (
            f"{PDF} is no longer covered by an ignore rule; the map states that "
            f"it is: {out.stdout or out.stderr}"
        )


def test_the_declaration_names_the_artifact():
    """The scope literal and the generator's constant must stay the same file.

    The literal cannot be replaced by the constant — the resolver parses this
    file instead of importing it — so the two are held together here rather than
    left to agree by luck.
    """
    assert OUTPUT_FILENAME in CROSSCUTTING_SCOPE


def test_the_module_never_reaches_for_the_clock():
    """Determinism is the whole basis of the freshness guard — hold it structurally."""
    # Both halves: the reader decides WHICH decision is in force, the renderer
    # prints it, and a clock in either would make every reissue differ.
    src = "".join(
        open(m.__file__, encoding="utf-8").read()
        for m in (release_roadmap, release_roadmap_composition)
    )
    for forbidden in ("import time", "datetime.now", "utcnow"):
        assert forbidden not in src, (
            f"{forbidden} in the generator would make every reissue differ and "
            "the staleness guard meaningless"
        )
