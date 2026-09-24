"""Text carrying a swallowed tool call is refused at the write boundary.

tool-call-syntax-leaks-into-entity-text (github#75). 64 entities of this project
(plus 23 journal lines) held the tail of a tool call: a field closed by its own
name, followed by the next parameter or invocation. Four tasks had lost their
complexity to it — a partial call accepted in silence. The guard sits on the
backend's one write path (_run_write) and names the field on updates.
"""

from __future__ import annotations

import pytest

from call_syntax_guard import LEAK, refuse_call_syntax
from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError

TAIL = 'Fix the gate.</goal>\n<parameter name="complexity">medium'


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "g.db")))
    s.epic_add("e", "E")
    s.story_add("e", "s", "S")
    s.task_add("s", "t", "T")
    yield s
    s.be.close()


def test_a_swallowed_call_in_a_task_field_is_refused_by_name(svc):
    with pytest.raises(ServiceError, match="Refused: goal contains the tail of a tool call"):
        svc.task_update("t", goal=TAIL)
    assert not svc.be.task_get("t")["goal"]


WRITERS = {
    "journal": lambda svc: svc.task_log("t", "done ✓</evidence>\n</invoke>"),
    "memory": lambda svc: svc.memory_add(
        "gotcha", "x", 'body</content>\n<parameter name="tags">["a"]'
    ),
}


@pytest.mark.parametrize("writer", sorted(WRITERS))
def test_every_writer_goes_through_the_one_boundary(svc, writer):
    """The guard is a property of the write path, not of each mutator."""
    with pytest.raises(ServiceError, match="tail of a tool call"):
        WRITERS[writer](svc)


@pytest.mark.parametrize(
    "prose",
    [
        pytest.param(
            'The goal ended in «</goal>» and then «<parameter name="complexity">».', id="quoted"
        ),
        pytest.param("Closing tags like </content> were counted: 25 of them.", id="counted"),
        pytest.param("HTML <b>bold</b> text", id="plain-html"),
    ],
)
def test_prose_about_the_syntax_is_not_refused(svc, prose):
    """NEGATIVE: a record that DESCRIBES the defect is kept."""
    svc.task_update("t", goal=prose)
    assert svc.be.task_get("t")["goal"] == prose


def test_the_malformed_tag_variant_is_caught():
    assert LEAK.search('pass.</evidence> <relevant_files">["a"]')


def test_the_refusal_is_raised_not_logged():
    """NEGATIVE: the caller sees it."""
    with pytest.raises(ServiceError):
        refuse_call_syntax([TAIL], ["goal"])
