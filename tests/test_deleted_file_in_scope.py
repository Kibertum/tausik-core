"""A deletion is part of the change, and declaring it must not break the gates.

MEASURED (session #235, live closure). The task that removed
`tests/test_doctor_doc_covers_every_check.py` declared it in `--relevant-files`,
which is the honest thing to do — the deletion IS part of that change. The
result:

    [FAIL] ruff (block)
           E902 Не удается найти указанный файл. (os error 2)
           --> tests\\test_doctor_doc_covers_every_check.py:1:1

The run came back `exit=1` with no verify handle. The only way past it was to
leave the deletion out of the declaration — verification_runs #2277 and #2278
are both recorded `under-declared` for exactly that reason.

WHY THAT IS WORSE THAN AN INCONVENIENCE. `declared_scope_status` is the number
this release set out to improve (decision #348), and the framework was itself
pushing the agent toward the answer that number counts as dishonest. A tool that
forces the dishonest answer has no standing to measure honesty.

THE FIX IS IN THE RUNNER AND NOWHERE ELSE. The declaration and the signed
receipt keep the full list, deletions included: the receipt describes the
CHANGE, and the change included removing a file. Only the command handed to a
file gate is filtered, because that command has to open what it is given.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import gate_outcome as _outcome  # noqa: E402
from gate_command_runner import run_command_gate  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]


def _ruff_gate() -> dict:
    return {
        "name": "ruff",
        "command": "ruff check {files}",
        "severity": "block",
        "file_extensions": [".py"],
    }


class TestADeletedFileNoLongerBreaksTheGate:
    """AC1. The exact shape that produced `E902` on a real closure."""

    def test_a_declaration_naming_a_deleted_file_still_passes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(_REPO)
        alive = "scripts/gate_outcome.py"
        gone = "tests/test_a_file_that_was_deleted_by_this_task.py"
        assert Path(_REPO / alive).is_file()
        assert not Path(_REPO / gone).exists()

        ok, output = run_command_gate(_ruff_gate(), [alive, gone])
        assert ok is True, output
        assert "E902" not in output

    def test_an_existing_file_is_not_lost_by_the_filter(self, tmp_path, monkeypatch):
        """AC4, the negative half: the filter must remove ONLY what is gone.
        A filter that quietly dropped live files would make the gate green by
        checking nothing, which is the failure mode this release is about."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "dirty.py").write_text("import os\n", encoding="utf-8")  # unused import

        ok, output = run_command_gate(_ruff_gate(), ["clean.py", "gone.py", "dirty.py"])
        assert ok is False, "the surviving offender must still be judged"
        assert "dirty.py" in output


class TestNothingLeftIsNotAVerdict:
    """AC3. A task whose whole product is deletions must not get a free green
    from a gate that had nothing to read."""

    def test_every_declared_file_gone_reports_not_applicable(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ok, output = run_command_gate(_ruff_gate(), ["gone_a.py", "gone_b.py"])
        assert "not a verdict" in output.lower() or "NOT_APPLICABLE" in output, output
        assert "2 declared file(s) are gone" in output

    def test_the_reason_code_is_its_own(self):
        """`all_files_deleted` and `no_matching_files` are different facts about
        a run, and only a code — not the sentence beside it — lets a query tell
        them apart."""
        assert _outcome.REASON_ALL_FILES_DELETED != _outcome.REASON_NO_MATCHING_FILES

    def test_an_empty_declaration_is_untouched_by_this(self, tmp_path, monkeypatch):
        """No declaration at all is a DIFFERENT state from 'everything declared
        is gone', and it already had its own handling. The new branch must not
        swallow it."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "any.py").write_text("x = 1\n", encoding="utf-8")
        ok, output = run_command_gate(_ruff_gate(), [])
        assert "declared file(s) are gone" not in output


class TestTheDeclarationItselfKeepsTheDeletion:
    """AC2. Only the command is filtered. The receipt describes the CHANGE, and
    the change included removing a file."""

    def test_scope_honesty_still_sees_a_declared_deletion(self, tmp_path):
        import verify_git_diff
        import verify_scope_honesty

        original = verify_git_diff.changed_files_since
        try:
            verify_git_diff.changed_files_since = lambda *a, **k: {  # type: ignore[assignment]
                "scripts/thing.py",
                "tests/test_gone.py",
            }
            result = verify_scope_honesty.describe_declared_scope(
                ["scripts/thing.py", "tests/test_gone.py"],
                "2026-01-01T00:00:00Z",
                root=str(tmp_path),
            )
        finally:
            verify_git_diff.changed_files_since = original  # type: ignore[assignment]

        assert result["status"] == "complete", result
        assert result["undeclared"] == []


@pytest.mark.parametrize("reason", ["all_files_deleted"])
def test_the_new_code_is_a_recognised_not_applicable_reason(reason):
    """A reason code the outcome layer does not know would be stored and never
    matched by anything — a value that looks recorded and is not."""
    assert reason in {
        value
        for name, value in vars(_outcome).items()
        if name.startswith("REASON_") and isinstance(value, str)
    }
