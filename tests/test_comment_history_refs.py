"""An event reference in a comment is a memory note filed where nobody looks.

MEASURED, session #277, and the measurement narrowed the target rather than
confirming it. Across 642 files 2584 references to project history sit in prose;
of those only 239, in 151 files, are in COMMENTS. The rest are in docstrings --
the declared home of the invariant, where "this literal is frozen because of
decision #646" IS the reason the code is that way. So the actionable number is
239, not 2584, and a check aimed at the larger number would have been a check
aimed at the project's strongest habit.

THE NEGATIVE HALF IS THE POINT. A guard that flagged reasoning would be switched
off the same week and would take the reasoning with it. The tests below feed it
real invariant prose from this tree and require silence.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import comment_history_refs as chr_  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "tests/"]


@pytest.fixture(scope="module")
def ratchet() -> dict:
    node = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
    return node["comment_history_refs"]


class TestAnEventReferenceIsRecognised:
    @pytest.mark.parametrize(
        ("text", "kind"),
        [
            pytest.param("ЗАМЕР смены #277: было 271", "session", id="session_ru"),
            pytest.param("session #241 found this", "session", id="session_en"),
            pytest.param("frozen by решение #646", "decision", id="decision_ru"),
            pytest.param("see decision #350 for the raise", "decision", id="decision_en"),
            pytest.param("конвенция #711 requires this", "knowledge", id="convention"),
            pytest.param("gotcha #201: no workspace variable", "knowledge", id="gotcha"),
            pytest.param("measured 2026-09-07 on the live tree", "date", id="iso_date"),
            pytest.param("MEASURED: 5782 calls", "measurement", id="measured_word"),
        ],
    )
    def test_each_address_into_the_record(self, text, kind):
        assert kind in chr_.event_refs(text)

    def test_several_kinds_are_all_reported(self):
        """The note says WHICH record is being duplicated, because a session and a
        date call for different memories."""
        kinds = chr_.event_refs("ЗАМЕР смены #277, 2026-09-26, решение #397")
        assert {"session", "date", "decision", "measurement"} <= set(kinds)


class TestReasoningIsLeftAlone:
    """The negative half. These are real sentences from this tree's docstrings."""

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param(
                "frozen literal: reading the live schema would mean something different every year",
                id="frozen_literal_rationale",
            ),
            pytest.param(
                "fail-open by construction: a scoping error must never hide tools",
                id="fail_open_rationale",
            ),
            pytest.param(
                "absolute paths, because the host expands no workspace variable",
                id="absolute_paths_rationale",
            ),
            pytest.param(
                "None means nothing to judge, not clean -- the caller skips such a file",
                id="none_semantics",
            ),
            pytest.param(
                "одна пустая строка между чужим текстом и нашим блоком", id="ru_invariant"
            ),
        ],
    )
    def test_invariant_prose_is_silent(self, text):
        assert chr_.event_refs(text) == []

    def test_a_bare_number_is_not_a_reference(self):
        """`#5` is a count, an issue in someone else's tracker, a column index. An
        address into OUR record is spelled with the record's name."""
        assert chr_.event_refs("keeps at most 5 entries") == []
        assert chr_.event_refs("raised to #147") == []


class TestDocstringsAreNotTheSubject:
    """A docstring is where the invariant lives; policing it would be policing the
    habit this project is built on."""

    def test_only_comments_are_collected(self):
        src = '"""ЗАМЕР смены #277 в докстринге."""\nx = 1  # ЗАМЕР смены #277 в комментарии\n'
        found = chr_.refs_in_source(src)
        assert len(found) == 1
        assert "комментарии" in found[0][1]

    def test_a_clean_file_reports_nothing(self):
        assert chr_.refs_in_source("x = 1  # holds the parsed value\n") == []

    def test_unparseable_source_yields_nothing_rather_than_raising(self):
        """A reminder must not fail on a file that does not compile anyway."""
        assert chr_.refs_in_source("def (:\n") == []


class TestOnlyWhatThisTaskAddedIsReported:
    """Reporting a note the author did not write is how a reminder becomes noise."""

    def _repo(self, tmp_path: Path) -> Path:
        subprocess.run(["git", "init", "-q", "."], cwd=tmp_path, check=True)
        target = tmp_path / "mod.py"
        target.write_text("x = 1  # ЗАМЕР смены #100: старая записка\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"],
            cwd=tmp_path,
            check=True,
        )
        return target

    def test_an_untouched_old_note_is_not_reported(self, tmp_path):
        target = self._repo(tmp_path)
        target.write_text(
            target.read_text(encoding="utf-8") + "y = 2  # holds the parsed value\n",
            encoding="utf-8",
        )
        assert chr_.new_refs_for_close(str(tmp_path), ["mod.py"]) == []

    def test_a_note_this_task_added_is_reported(self, tmp_path):
        target = self._repo(tmp_path)
        target.write_text(
            target.read_text(encoding="utf-8") + "z = 3  # решение #399: так решено\n",
            encoding="utf-8",
        )
        found = chr_.new_refs_for_close(str(tmp_path), ["mod.py"])
        assert [f[0] for f in found] == ["mod.py"]
        assert "decision" in found[0][2]

    def test_no_git_yields_nothing(self, tmp_path):
        """A closure must not hinge on the shape of someone's working tree."""
        assert chr_.new_refs_for_close(str(tmp_path), ["mod.py"]) == []


class TestTheNoteNamesTheFix:
    def test_silence_when_nothing_was_added(self):
        assert chr_.closure_note("slug", []) is None

    def test_the_note_carries_the_command_and_the_slug(self):
        note = chr_.closure_note("my-task", [("scripts/x.py", "ЗАМЕР смены #277", ["session"])])
        assert "memory add" in note and "my-task" in note

    def test_the_note_says_the_invariant_stays(self):
        """Without this line the reminder reads as "write fewer comments", which is
        the instruction this project refuses to give."""
        note = chr_.closure_note("t", [("a.py", "решение #1", ["decision"])])
        assert "ИНВАРИАНТА" in note


class TestClosureAsksTheQuestion:
    """A module that works and nobody calls is the class this release removes."""

    def test_the_closure_path_collects_the_note(self):
        import closure_reminders

        assert hasattr(closure_reminders, "_comment_note")
        source = (_REPO / "scripts" / "closure_reminders.py").read_text(encoding="utf-8")
        assert "_comment_note(slug, task)" in source

    def test_a_task_without_declared_python_files_is_silent(self):
        import closure_reminders

        assert closure_reminders._comment_note("t", {"relevant_files": '["docs/x.md"]'}) is None


class TestRemainderDoesNotGrow:
    def test_comment_references_do_not_grow(self, ratchet):
        total = 0
        files = 0
        for sub in ("scripts", "bootstrap", "harness", "tests"):
            for path in (_REPO / sub).rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                found = chr_.refs_in_source(path.read_text(encoding="utf-8"))
                if found:
                    total += len(found)
                    files += 1
        assert total <= ratchet["comment_refs"], (
            f"event references in comments GREW: {total} > {ratchet['comment_refs']} "
            f"(in {files} files). A note about what happened belongs in memory."
        )

    def test_the_reason_sits_next_to_the_number(self, ratchet):
        comment = ratchet["_baseline_comment"]
        assert "2584" in comment and "докстринг" in comment
        assert "только уменьшаться" in comment


class TestTheHashInsideAStringIsNotAComment:
    """The bug this class exists for was found by the test above, not by review.

    The first version accepted only lines that BEGIN with a hash, and so missed
    the commonest shape of a working note: a tail on a line of code. Fixing it by
    splitting on the first hash would have introduced the opposite error, because
    a hash lives inside string literals -- `"github#7"` is a ticket reference this
    very repository stores.
    """

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            pytest.param("z = 3  # решение #399", "решение #399", id="trailing_comment"),
            pytest.param("# ЗАМЕР смены #277", "ЗАМЕР смены #277", id="whole_line"),
            pytest.param('REF = "github#7"', "", id="hash_inside_double_quotes"),
            pytest.param("REF = 'gitlab#12'", "", id="hash_inside_single_quotes"),
            pytest.param('S = "# not a comment"  # ЗАМЕР', "ЗАМЕР", id="literal_then_comment"),
            pytest.param(
                'P = "a\\\\"  # решение #1', "решение #1", id="escaped_quote_then_comment"
            ),
            pytest.param("value = 1", "", id="no_comment"),
        ],
    )
    def test_comment_part_reads_only_the_comment(self, line, expected):
        assert chr_.comment_part(line) == expected


class TestASpecVersionIsNotAProjectEvent:
    """MEASURED FIRST, and the number decided the shape of the fix.

    Of the 237 comment references in the remainder, 2 are the dated version of an
    external specification -- both "MCP 2026-07-28". Two is small, and the honest
    reading is that it does not justify a broad rule: what justifies one is that
    the class grows with every standard the project reads, and a finding nobody can
    act on teaches everyone to skip its whole category.

    So the rule is as narrow as the measurement supports: the standard's name
    first, within a short reach, and the other four kinds of reference untouched.
    """

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param(
                "MCP 2026-07-28 (SEP-2549) lets a client cache tools/list for a ttl",
                id="mcp_with_sep",
            ),
            pytest.param(
                "(MCP 2026-07-28 CacheableResult): a client must not reuse a stale surface",
                id="mcp_cacheable_result",
            ),
            pytest.param("RFC 9457, 2026-01-15, fixes the media type", id="rfc_date_after_number"),
            pytest.param("shape mandated by SENAR 2026-04-02", id="senar_version"),
            pytest.param("iso 2026-03-01 renamed the field", id="lowercase_name"),
        ],
    )
    def test_a_dated_standard_is_not_reported(self, text):
        assert "date" not in chr_.event_refs(text)

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("переписано 2026-09-26", id="bare_project_date"),
            pytest.param("2026-09-26: ratchet lowered to zero", id="date_leads_the_line"),
            pytest.param(
                "MCP surface reworked, and on 2026-09-26 the count finally reached zero",
                id="name_too_far_from_the_date",
            ),
        ],
    )
    def test_a_project_date_is_still_reported(self, text):
        """The narrowing must not cost the check its subject.

        The third case is the boundary: a standard's name appears, but 30 characters
        of project narrative separate it from the date, and that is a project event
        mentioning a standard rather than a standard's version.
        """
        assert "date" in chr_.event_refs(text)

    def test_both_dates_are_weighed_not_just_the_first(self):
        """A line carrying a spec version AND a project date keeps the reference.

        Masking is per occurrence, not per line: dropping the whole line would lose
        the second date, which is the one that belongs in memory.
        """
        text = "brought to MCP 2026-07-28 during the rewrite of 2026-09-26"
        assert "date" in chr_.event_refs(text)

    def test_the_other_kinds_ignore_the_mask(self):
        """Only the date check reads the masked text.

        A sentence can name a standard's version and still duplicate a session
        record; masking the whole sentence would have hidden the session too.
        """
        assert chr_.event_refs("смена #277 привела код к MCP 2026-07-28") == ["session"]

    def test_the_two_real_lines_in_the_tree_are_silent(self):
        """Read off the files rather than retyped, so a reword cannot fake a pass."""
        for rel in ("scripts/mcp_tool_scope.py", "harness/claude/mcp/project/server.py"):
            source = (_REPO / rel).read_text(encoding="utf-8")
            dated = [
                (line, text) for line, text, kinds in chr_.refs_in_source(source) if "date" in kinds
            ]
            assert dated == [], f"{rel}: {dated}"
