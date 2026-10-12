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
from datetime import date
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import comment_history_refs as chr_  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "tests/"]


def test_ratchet_uses_task_baseline_instead_of_an_aggregate_allowance():
    """The fast ratchet lane must execute the guard for this non-numeric contract."""
    gates = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
    ratchet = gates["comment_history_refs"]

    assert "task-baseline" in ratchet["tracking"]
    assert not any(isinstance(value, (int, float)) for value in ratchet.values())


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
        assert chr_.task_baseline.anchor(str(tmp_path), "t") is not None
        return target

    def test_an_untouched_old_note_is_not_reported(self, tmp_path):
        target = self._repo(tmp_path)
        target.write_text(
            target.read_text(encoding="utf-8") + "y = 2  # holds the parsed value\n",
            encoding="utf-8",
        )
        scan = chr_.new_refs_for_close(str(tmp_path), "t", ["mod.py"])
        assert scan.checked and scan.findings == ()

    def test_a_note_this_task_added_is_reported(self, tmp_path):
        target = self._repo(tmp_path)
        target.write_text(
            target.read_text(encoding="utf-8") + "z = 3  # решение #399: так решено\n",
            encoding="utf-8",
        )
        scan = chr_.new_refs_for_close(str(tmp_path), "t", ["mod.py"])
        assert [f[0] for f in scan.findings] == ["mod.py"]
        assert "decision" in scan.findings[0][2]

    def test_no_git_is_not_checked_not_clean(self, tmp_path):
        scan = chr_.new_refs_for_close(str(tmp_path), "t", ["mod.py"])
        assert not scan.checked and scan.reason

    @pytest.mark.parametrize("state", ["committed", "staged", "unstaged", "untracked"])
    def test_baseline_sees_every_live_git_state(self, tmp_path, state):
        target = self._repo(tmp_path)
        if state == "untracked":
            target = tmp_path / "new.py"
        target.write_text("x = 1  # decision #399\n", encoding="utf-8")
        if state in {"staged", "committed"}:
            subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        if state == "committed":
            subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "wip"],
                cwd=tmp_path,
                check=True,
            )

        scan = chr_.new_refs_for_close(str(tmp_path), "t", [target.name])
        assert scan.checked and len(scan.findings) == 1

    def test_rename_keeps_added_comment_visible(self, tmp_path):
        target = self._repo(tmp_path)
        renamed = tmp_path / "renamed.py"
        target.rename(renamed)
        renamed.write_text("x = 1  # decision #399\n", encoding="utf-8")

        scan = chr_.new_refs_for_close(str(tmp_path), "t", ["renamed.py"])
        assert scan.checked and scan.findings[0][0] == "renamed.py"

    def test_unchanged_rename_does_not_re_report_old_comment(self, tmp_path):
        target = self._repo(tmp_path)
        subprocess.run(["git", "mv", target.name, "renamed.py"], cwd=tmp_path, check=True)

        scan = chr_.new_refs_for_close(str(tmp_path), "t", ["renamed.py"])
        assert scan.checked and scan.findings == ()

    def test_deleting_old_reference_cannot_launder_a_new_one(self, tmp_path):
        old = self._repo(tmp_path)
        old.write_text("x = 1  # invariant only\n", encoding="utf-8")
        new = tmp_path / "new.py"
        new.write_text("x = 1  # decision #399\n", encoding="utf-8")

        scan = chr_.new_refs_for_close(str(tmp_path), "t", ["mod.py", "new.py"])
        assert [finding[0] for finding in scan.findings] == ["new.py"]

    def test_unicode_tracked_path_is_not_lost_in_patch_headers(self, tmp_path):
        self._repo(tmp_path)
        target = tmp_path / "módulo.py"
        target.write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", str(target.name)], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "add"],
            cwd=tmp_path,
            check=True,
        )
        target.write_text("x = 1  # decision #399\n", encoding="utf-8")

        scan = chr_.new_refs_for_close(str(tmp_path), "t", [target.name])
        assert scan.checked and scan.findings[0][0] == target.name

    def test_untracked_symlink_is_not_read(self, tmp_path):
        self._repo(tmp_path)
        outside = tmp_path.parent / "outside.py"
        outside.write_text("x = 1  # decision #399\n", encoding="utf-8")
        link = tmp_path / "linked.py"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("host does not permit file symlinks")

        scan = chr_.new_refs_for_close(str(tmp_path), "t", [link.name])
        assert not scan.checked and scan.findings == ()

    def test_oversized_untracked_file_is_not_echoed(self, tmp_path):
        self._repo(tmp_path)
        target = tmp_path / "large.py"
        target.write_text("# decision #399\n" + "x" * 1_000_000, encoding="utf-8")

        scan = chr_.new_refs_for_close(str(tmp_path), "t", [target.name])
        assert not scan.checked and scan.findings == ()

    def test_unicode_untracked_path_is_not_lost(self, tmp_path):
        self._repo(tmp_path)
        target = tmp_path / "новый.py"
        target.write_text("x = 1  # decision #399\n", encoding="utf-8")

        scan = chr_.new_refs_for_close(str(tmp_path), "t", [target.name])
        assert scan.checked and scan.findings[0][0] == target.name

    def test_many_paths_use_a_bounded_number_of_git_calls(self, tmp_path, monkeypatch):
        self._repo(tmp_path)
        paths = []
        for index in range(25):
            rel = f"many_{index}.py"
            (tmp_path / rel).write_text("x = 1  # decision #399\n", encoding="utf-8")
            paths.append(rel)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        real_run = chr_.subprocess.run
        calls = []

        def counted_run(*args, **kwargs):
            calls.append(args[0])
            return real_run(*args, **kwargs)

        monkeypatch.setattr(chr_.subprocess, "run", counted_run)
        scan = chr_.new_refs_for_close(str(tmp_path), "t", paths)

        assert scan.checked and len(scan.findings) == 25
        # One baseline lookup plus one tree diff and one untracked-files query.
        assert len(calls) == 3


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


def test_not_checked_is_visible_at_closure():
    note = chr_.closure_note("t", chr_.CommentRefScan(False, reason="baseline missing"))
    assert "not checked" in note and "baseline missing" in note


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

    def test_missing_baseline_is_visible_in_closure_output(self, tmp_path, monkeypatch):
        import closure_reminders
        import project_config

        (tmp_path / ".tausik").mkdir()
        monkeypatch.setattr(project_config, "find_tausik_dir", lambda: str(tmp_path / ".tausik"))

        note = closure_reminders._comment_note("t", {"relevant_files": '["mod.py"]'})
        assert note and "not checked" in note

    def test_unexpected_scan_error_is_visible_not_silent(self, monkeypatch):
        import closure_reminders
        import project_config

        def fail_root():
            raise RuntimeError("boom")

        monkeypatch.setattr(project_config, "find_tausik_dir", fail_root)
        note = closure_reminders._comment_note("t", {"relevant_files": '["mod.py"]'})
        assert note and "not checked" in note and "RuntimeError" in note


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
            pytest.param("CVE 2026-09-01 disclosure window", id="cve_version"),
        ],
    )
    def test_a_dated_standard_is_not_reported(self, text):
        assert "date" not in chr_.event_refs(text)

    def test_a_lowercase_acronym_was_wrongly_accepted_here_and_no_longer_is(self):
        """This case used to read `iso 2026-03-01` and assert silence. It was wrong.

        Kept as a named test rather than deleted, because the correction is the
        lesson: `iso` and `sep` are ordinary words in this tree, and accepting them
        as spec names let an everyday sentence launder a date. The case that replaced
        it above uses upper case, the way a real citation is written.
        """
        assert "date" in chr_.event_refs("iso 2026-03-01 renamed the field")

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


class TestFutureDatesNeedAnOwnerAndAction:
    @pytest.mark.parametrize(
        "text",
        [
            "deadline 2099-04-02 owner=release action=renew",
            "expiry 2099-04-02 owner=security@example.com action=rotate-key",
        ],
    )
    def test_owned_future_action_is_not_history(self, text):
        assert "date" not in chr_.event_refs(text, today=date(2026, 10, 12))

    @pytest.mark.parametrize(
        "text",
        [
            "deadline 2099-04-02",
            "deadline 2099-04-02 owner=release",
            "expires 2099-04-02 owner=release action=renew",
            "2099-04-02 owner=release action=renew",
            "deadline 2020-04-02 owner=release action=renew",
            "deadline 2099-04-02 owner=release action=renew; milestone 2099-05-03",
        ],
    )
    def test_ambiguous_future_date_stays_reportable(self, text):
        assert "date" in chr_.event_refs(text, today=date(2026, 10, 12))


class TestTheModuleCarriesNoNoteOfItsOwn:
    """The detector's own source is the one file it must be clean of.

    MEASURED: of 236 references in the remainder exactly one was a quoted example,
    and it was in this module -- an illustration of the rule, spelled out with a
    real date. One case in 236 did not justify an ILLUSTRATIVE class, and the class
    would have cost more than it saved: a rule keyed on quotation marks misfires on
    English possessives, and `task's defect ... `[FAIL] pytest`` already reads as a
    quoted span to a naive scanner.

    A LIMITATION FOUND BY THE SAME MEASUREMENT, and the reason the example is now
    described rather than quoted: a quotation that wraps is invisible here. The
    opening mark landed on one line and the closing mark on the next, and
    `comment_lines` reads one line at a time. Seeing it would mean joining
    consecutive comment lines into blocks, which would change the file-and-line
    report the closure note prints.
    """

    def test_the_detector_source_is_clean(self):
        source = (_REPO / "scripts" / "comment_history_refs.py").read_text(encoding="utf-8")
        found = chr_.refs_in_source(source)
        assert found == [], f"the detector carries {len(found)} note(s) of its own: {found}"

    def test_a_wrapped_quotation_is_still_invisible(self):
        """The limitation is pinned so nobody claims a coverage that does not exist.

        If someone later joins comment lines into blocks, this test fails and asks
        them to say so on purpose rather than discovering it by surprise.
        """
        wrapped = '# Name FIRST only: "2026-09-26, замер\n# по MCP" is a project date\n'
        assert [kinds for _line, _text, kinds in chr_.refs_in_source(wrapped)] == [["date"]]


class TestAStandardsNameDoesNotLaunderAProjectDate:
    """The rule must prove the date IS the standard's version, not merely near its name.

    FOUND BY ADVERSARIAL REVIEW of the commit that added the rule, and it is the
    failure the rule was built to prevent: the first version checked only that a
    name preceded a date within 24 characters, with any prose allowed in between.
    So "MCP support added on 2026-09-26" -- a plain sentence about work done here --
    had its date erased, and the detector acquired a blind spot in exactly its own
    subject.

    The gap survived my own negative half because that half asked two questions and
    not the third: reverse order, and a name too far away. It never asked what
    happens when the name is used CORRECTLY and the date still belongs to the
    project. Same shape as convention #755.
    """

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("MCP support added on 2026-09-26", id="added_on"),
            pytest.param("ISO week parsing landed 2026-09-26", id="landed"),
            pytest.param("RFC compliance fixed 2026-09-26", id="fixed"),
            pytest.param("SENAR audit run on 2026-09-01", id="audit_run"),
            pytest.param("dropped the MCP shim, 2026-09-26", id="dropped_the_shim"),
        ],
    )
    def test_prose_about_our_own_work_keeps_its_date(self, text):
        assert "date" in chr_.event_refs(text), text

    @pytest.mark.parametrize("name", chr_._EXTERNAL_STANDARDS)
    def test_every_name_is_checked_not_just_the_one_that_was_reported(self, name):
        """Each of the twelve, because the next name added must be covered too.

        A regression test written for the reported case only would pass while the
        eleven others stayed broken, and a later addition to the list would arrive
        with no coverage at all.
        """
        assert "date" in chr_.event_refs(f"{name} handling landed on 2026-09-26")

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("MCP 2026-07-28 CacheableResult", id="name_then_date"),
            pytest.param("RFC 9457, 2026-01-15, fixes the media type", id="number_between"),
            pytest.param("shape mandated by SENAR 2026-04-02", id="mandated_by"),
            pytest.param("MCP (2026-07-28) — the revision we answer to", id="parenthesised"),
            pytest.param("SEP-2549 / 2026-07-28", id="sep_number_and_slash"),
        ],
    )
    def test_a_version_citation_is_still_not_an_event(self, text):
        """The narrowing must not undo the rule it narrows.

        Only version-shaped characters may sit between the name and the date:
        digits, dots, dashes, parens, commas, slashes, spaces. That admits every
        real citation in this tree and no sentence.
        """
        assert "date" not in chr_.event_refs(text), text

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("sep argument added 2026-09-26", id="os_sep"),
            pytest.param("iso-8601 helper landed 2026-09-26", id="iso_8601_lowercase"),
            pytest.param("pep talk on 2026-09-26", id="pep_lowercase"),
        ],
    )
    def test_a_lowercase_acronym_is_an_ordinary_word(self, text):
        """`sep` and `iso` are everyday vocabulary HERE, not spec citations.

        `os.sep`, `sep=` and `ISO-8601` appear dozens of times across scripts, tests
        and harness. Matching case-insensitively made every one of them able to
        launder a date, which is why the names are now recognised in upper case --
        the way real citations of these standards are always written.
        """
        assert "date" in chr_.event_refs(text), text


class TestTheGapAdmitsAVersionAndNotASentence:
    """The second correction, caught by measurement rather than by review.

    Tightening the rule should only ever RAISE the count of references, because
    fewer dates get masked. It fell by one instead, and that number was the tell: the
    first correction admitted a bare period into the gap so a version like `1.2.3`
    would fit, and a period is also a sentence boundary. A dot now reaches the gap
    only inside a version token.
    """

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("MCP. 2026-09-26 shipped", id="period_is_a_sentence_boundary"),
            pytest.param("RFC 9457. 2026-09-26 we dropped it", id="period_after_a_version"),
            pytest.param("PEP 8. On 2026-09-26 the formatter changed", id="period_then_prose"),
        ],
    )
    def test_a_new_sentence_keeps_its_date(self, text):
        assert "date" in chr_.event_refs(text), text

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("MCP v1.2.3 (2026-07-28)", id="dotted_version_prefixed_with_v"),
            pytest.param("SEP-2549 / 2026-07-28", id="number_and_slash"),
            pytest.param("ISO 8601:2026-04-02", id="colon_between"),
        ],
    )
    def test_a_dotted_version_still_reaches_its_date(self, text):
        """A dot inside a version token must not break the rule it was let in for."""
        assert "date" not in chr_.event_refs(text), text
