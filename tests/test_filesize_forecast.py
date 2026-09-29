"""The line cap, answered while the write is still in the author's hand.

THE MEASUREMENT. Of 285 red verify runs, `filesize` is 16.1%, and it is not history — 20
fell in September alone, second only to `bootstrap_drift`. A red run is expensive: tasks
with none cost a median 51k tokens, one red 78k, two 123k. And this red is arithmetic: the
cap is a number and the file is on disk at the moment of the write.

WHAT MUST NOT HAPPEN IS A WRONG WARNING. An author who learns that these lines are
sometimes wrong stops reading them, and then the measurement above returns. So everything
unknowable resolves to silence: an unreadable file, a payload this cannot compute from, a
replace_all whose occurrence count is not in the payload. The cost of silence is one red
verify — which is the state before this existed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import filesize_forecast as fc  # noqa: E402
from gate_filesize import DEFAULT_MAX_LINES  # noqa: E402

CAP = DEFAULT_MAX_LINES


def _write(n: int) -> dict:
    return {"file_path": "scripts/thing.py", "content": "x\n" * n}


class TestAWriteThatCrossesTheCap:
    def test_it_names_the_file_the_count_and_the_cap(self, tmp_path):
        """AC-1. A warning that says only "too long" sends the reader to count by hand."""
        note = fc.forecast("Write", _write(CAP + 40), str(tmp_path))
        assert "scripts/thing.py" in note
        assert str(CAP + 40) in note and str(CAP) in note
        assert "LINE CAP" in note

    def test_a_file_comfortably_under_the_cap_says_nothing(self, tmp_path):
        assert fc.forecast("Write", _write(CAP - fc.NEAR - 10), str(tmp_path)) == ""

    def test_approaching_the_cap_is_said_differently_from_crossing_it(self, tmp_path):
        """One is a refusal waiting to happen, the other has already happened. Wording them
        the same would teach the reader to treat both as noise."""
        near = fc.forecast("Write", _write(CAP - 5), str(tmp_path))
        over = fc.forecast("Write", _write(CAP + 5), str(tmp_path))
        assert "short of the cap" in near and "over the cap" not in near
        assert "over the cap" in over


class TestAnEditIsComputedFromItsDelta:
    def test_the_delta_is_applied_to_the_file_on_disk(self, tmp_path):
        """AC-2. Guessing at the result would warn about a size nobody is writing."""
        target = tmp_path / "scripts"
        target.mkdir()
        (target / "thing.py").write_text("x\n" * (CAP - 2), encoding="utf-8")
        note = fc.forecast(
            "Edit",
            {"file_path": "scripts/thing.py", "old_string": "x", "new_string": "a\nb\nc\nd\ne"},
            str(tmp_path),
        )
        assert str(CAP + 2) in note, "current lines plus the delta, not a guess"

    def test_an_edit_that_shrinks_the_file_says_nothing(self, tmp_path):
        target = tmp_path / "scripts"
        target.mkdir()
        (target / "thing.py").write_text("x\n" * (CAP + 10), encoding="utf-8")
        note = fc.forecast(
            "Edit",
            {"file_path": "scripts/thing.py", "old_string": "x\n" * 200, "new_string": "x"},
            str(tmp_path),
        )
        assert note == "", "the edit takes it under the cap; there is nothing to warn about"


class TestSilenceWhereverTheAnswerIsNotKnown:
    def test_a_replace_all_is_not_guessed_at(self, tmp_path):
        """NEGATIVE, AC-5. The occurrence count is not in the payload, so the delta is a
        lower bound; naming a figure that is wrong whenever the string repeats is how a
        warning loses its reader."""
        target = tmp_path / "scripts"
        target.mkdir()
        (target / "thing.py").write_text("x\n" * (CAP - 1), encoding="utf-8")
        note = fc.forecast(
            "Edit",
            {
                "file_path": "scripts/thing.py",
                "old_string": "x",
                "new_string": "a\nb\nc",
                "replace_all": True,
            },
            str(tmp_path),
        )
        assert note == ""

    def test_an_edit_on_a_file_that_is_not_there_says_nothing(self, tmp_path):
        note = fc.forecast(
            "Edit",
            {"file_path": "scripts/gone.py", "old_string": "x", "new_string": "y\nz"},
            str(tmp_path),
        )
        assert note == ""

    @pytest.mark.parametrize(
        "payload",
        [{}, {"file_path": ""}, {"file_path": "scripts/x.py"}, {"content": "x"}],
        ids=["empty", "blank_path", "no_content", "no_path"],
    )
    def test_a_payload_it_cannot_read_produces_nothing(self, payload, tmp_path):
        assert fc.forecast("Write", payload, str(tmp_path)) == ""

    @pytest.mark.parametrize("tool", ["Bash", "Read", "MultiEdit", ""])
    def test_a_tool_whose_result_is_not_computable_produces_nothing(self, tool, tmp_path):
        assert fc.forecast(tool, _write(CAP + 100), str(tmp_path)) == ""


class TestItAsksTheGatesOwnQuestion:
    def test_an_exempt_path_is_silent(self, tmp_path):
        """NEGATIVE, AC-4. A warning about a file the gate exempts is noise about something
        that will never go red, and noise is what gets the whole line skipped."""
        payload = {"file_path": "tests/test_thing.py", "content": "x\n" * (CAP + 100)}
        assert fc.forecast("Write", payload, str(tmp_path)) == ""

    def test_the_exemption_comes_from_the_gate_rather_than_a_copy(self):
        """AC-6. Two copies of the rules drift, and then they disagree exactly when it
        matters. This asserts the forecast imports the gate's predicate."""
        text = (_REPO / "scripts" / "filesize_forecast.py").read_text(encoding="utf-8")
        assert "from gate_filesize import" in text and "is_exempt" in text

    def test_the_cap_is_the_gates_cap(self, tmp_path):
        """A gate carrying its own max_lines must move the warning with it."""
        payload = {"file_path": "scripts/thing.py", "content": "x\n" * 60}
        assert fc.forecast("Write", payload, str(tmp_path), {"max_lines": 50}) != ""
        assert fc.forecast("Write", payload, str(tmp_path), {"max_lines": 5000}) == ""


class TestTheHookOnlyEverAdvises:
    def test_the_allow_path_returns_zero_whatever_the_forecast_says(self):
        """NEGATIVE, AC-3. Refusing a write mid-task leaves a half-applied change and no
        way to finish the thought; splitting a file is a decision, not a reflex."""
        text = (_REPO / "scripts" / "hooks" / "scope_write_gate.py").read_text(encoding="utf-8")
        body = text[text.index("def _allow_with_forecast") :]
        body = body[: body.index("\ndef ", 1)]
        assert "return 2" not in body, "the advisory path has no refusal in it"
        assert body.count("return 0") >= 2, "every way out of it allows the write"
        assert "additionalContext" in body

    def test_a_failure_inside_the_advice_never_decides_the_write(self):
        text = (_REPO / "scripts" / "hooks" / "scope_write_gate.py").read_text(encoding="utf-8")
        body = text[text.index("def _allow_with_forecast") :]
        assert "except Exception" in body[: body.index("\ndef ", 1)]


class TestTheNoteForAFileAlreadyOnDisk:
    def test_an_oversized_file_is_named_with_its_count(self, tmp_path):
        target = tmp_path / "scripts"
        target.mkdir()
        (target / "thing.py").write_text("x\n" * (CAP + 3), encoding="utf-8")
        note = fc.current_size_note("scripts/thing.py", str(tmp_path))
        assert str(CAP + 3) in note

    @pytest.mark.parametrize("name", ["scripts/small.py", "scripts/gone.py"])
    def test_a_file_within_the_cap_or_absent_says_nothing(self, name, tmp_path):
        target = tmp_path / "scripts"
        target.mkdir()
        (target / "small.py").write_text("x\n" * 10, encoding="utf-8")
        assert fc.current_size_note(name, str(tmp_path)) == ""
