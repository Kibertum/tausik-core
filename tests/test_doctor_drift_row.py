"""Doctor's "Bootstrap drift" row, moved out of `project_cli_doctor` when that
file reached the filesize cap to the line (review #207, record #10).

The three answers are the ones doctor always printed; this pins them so the
move is a move and not a rewrite.
"""

from __future__ import annotations

import os
import sys

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from service_doctor_drift import format_scripts_drift_line  # noqa: E402


def test_cannot_compare_is_a_warning_that_says_so():
    is_warn, detail = format_scripts_drift_line(None)
    assert is_warn is True
    assert detail == "could not compare scripts/ vs deployed profiles"


def test_drift_names_the_files_and_the_redeploy_command():
    is_warn, detail = format_scripts_drift_line([".claude/scripts/a.py", ".cursor/scripts/a.py"])
    assert is_warn is True
    assert detail.startswith(
        "2 deployed file(s) differ: .claude/scripts/a.py, .cursor/scripts/a.py"
    )
    assert "python bootstrap/bootstrap.py --ide all" in detail
    assert "more" not in detail


def test_more_than_eight_files_are_counted_not_listed():
    names = [f".claude/scripts/f{i}.py" for i in range(11)]
    is_warn, detail = format_scripts_drift_line(names)
    assert is_warn is True
    assert "11 deployed file(s) differ" in detail
    assert "(+3 more)" in detail
    assert ".claude/scripts/f8.py" not in detail


def test_in_sync_is_the_ok_row():
    assert format_scripts_drift_line([]) == (False, "none — deployed scripts match source")


def test_the_doctor_uses_the_moved_row_and_has_headroom_again():
    path = os.path.join(SCRIPTS, "project_cli_doctor.py")
    with open(path, encoding="utf-8") as fh:
        body = fh.read()
    assert "_format_scripts_drift_line(" in body
    assert "deployed file(s) differ" not in body, "the row text must live in one place"
    assert body.count("\n") <= 490, "the file is back at the cap"
