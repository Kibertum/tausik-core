"""GitLab #13: a comma-joined `--relevant-files` value is refused, not stored as one path.

`task update <slug> --relevant-files "a.py,b.py,c.py"` stored ONE element and
said "Task updated."; the refusal came later from `verify`, worded as "No tests
mapped for ['a.py,b.py,c.py']" — a project problem, not a corrupted input. Every
test here asserts the STORED VALUE next to the refusal: a validator that
refuses and writes anyway would pass a refusal-only check.

The comma is not split silently — a comma is legal in a file name — so the
one honest case (a file whose name carries a comma and exists) is accepted,
and only the element that resolves to nothing is refused, by the right form.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_TESTS = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_TESTS, "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService, ServiceError  # noqa: E402
from relevant_files_input import RIGHT_FORM, check_declared_paths  # noqa: E402
from task_done_scope import persist_declared_scope  # noqa: E402


@pytest.fixture
def project(tmp_path):
    """A project root with `.tausik/tausik.db` — the layout the validator
    resolves relative declarations against — and one task to declare on."""
    (tmp_path / ".tausik").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "scripts" / "b.py").write_text("", encoding="utf-8")
    be = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    svc = ProjectService(be)
    svc.epic_add("v1", "Version 1")
    svc.story_add("v1", "setup", "Setup")
    svc.task_add("setup", "subject", "Subject", goal="a goal", complexity="simple")
    yield tmp_path, svc, be
    be.close()


def _stored(be, slug="subject"):
    raw = be.task_get(slug).get("relevant_files")
    return json.loads(raw) if raw else None


class TestACommaJoinedValueIsRefusedByTheRightForm:
    def test_update_refuses_and_stores_nothing(self, project):
        root, svc, be = project
        with pytest.raises(ServiceError) as err:
            svc.task_update("subject", relevant_files=json.dumps(["scripts/a.py,scripts/b.py"]))
        assert "carries a comma" in str(err.value)
        assert RIGHT_FORM in str(err.value), "the refusal must name the form that was meant"
        assert _stored(be) is None, "refused AND written — the refusal-only check would pass this"

    def test_task_done_declaration_is_judged_the_same_way(self, project):
        """`task done --relevant-files` writes through the backend, not the
        service; the same validator must stand there or the two entry points
        disagree on what a declaration is."""
        root, svc, be = project
        with pytest.raises(ServiceError) as err:
            persist_declared_scope(
                be, "subject", ["scripts/a.py,scripts/b.py"], str(root / ".tausik")
            )
        assert RIGHT_FORM in str(err.value)
        assert _stored(be) is None

    def test_a_space_separated_list_is_stored_as_given(self, project):
        root, svc, be = project
        svc.task_update("subject", relevant_files=json.dumps(["scripts/a.py", "scripts/b.py"]))
        assert _stored(be) == ["scripts/a.py", "scripts/b.py"]


class TestTheCommaIsNotSplitSilently:
    def test_an_existing_path_with_a_comma_in_its_name_is_accepted(self, project):
        """Negative boundary: a comma is legal in a file name. Splitting the
        common mistake would break the honest case."""
        root, svc, be = project
        (root / "scripts" / "a,b.py").write_text("", encoding="utf-8")
        svc.task_update("subject", relevant_files=json.dumps(["scripts/a,b.py"]))
        assert _stored(be) == ["scripts/a,b.py"]


class TestAMissingPathIsAWarningNotARefusal:
    def test_update_warns_and_stores(self, project):
        root, svc, be = project
        reply = svc.task_update(
            "subject", relevant_files=json.dumps(["scripts/a.py", "scripts/new.py"])
        )
        assert "not on disk yet" in reply and "scripts/new.py" in reply
        assert _stored(be) == ["scripts/a.py", "scripts/new.py"], (
            "a warning must not block the write"
        )

    def test_no_warning_when_every_path_exists(self, project):
        root, svc, be = project
        reply = svc.task_update("subject", relevant_files=json.dumps(["scripts/a.py"]))
        assert "not on disk" not in reply

    def test_the_validator_judges_relative_paths_against_the_project(self, tmp_path):
        (tmp_path / "x.py").write_text("", encoding="utf-8")
        assert check_declared_paths(["x.py"], str(tmp_path)) == []
        assert check_declared_paths(["y.py"], str(tmp_path))[0].startswith("NOTE: 1 declared path")

    def test_a_backslash_declaration_is_read_as_the_same_path(self, tmp_path):
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "x.py").write_text("", encoding="utf-8")
        assert check_declared_paths(["pkg\\x.py"], str(tmp_path)) == []

    def test_a_single_not_yet_created_name_with_a_comma_is_a_note_not_a_refusal(self, tmp_path):
        """Boundary of the heuristic (review, session #252): the corruption
        shape is two or more pieces that each look like a path. One piece
        without a separator or extension is a file the task may be creating."""
        lines = check_declared_paths(["draft,v2"], str(tmp_path))
        assert lines and "draft,v2" in lines[0]

    def test_task_done_shows_the_same_note_as_update(self, project):
        root, svc, be = project
        notices: list[str] = []
        persist_declared_scope(be, "subject", ["scripts/new.py"], str(root / ".tausik"), notices)
        assert notices and "not on disk yet" in notices[0]
        assert _stored(be) == ["scripts/new.py"]


def test_the_help_text_no_longer_invites_the_comma():
    """The parser said "JSON-list" — the STORAGE shape — and a reader took it
    as the input format. The help must name the input form."""
    from project_parser_task import add_task  # noqa: F401
    import argparse

    parser = argparse.ArgumentParser(prog="tausik")
    sub = parser.add_subparsers(dest="command")
    add_task(sub)
    task_sub = next(
        a for a in sub.choices["task"]._actions if isinstance(a, argparse._SubParsersAction)
    )
    help_text = task_sub.choices["update"].format_help()
    assert "SPACE-separated" in help_text
    assert "JSON-list scope" not in help_text
