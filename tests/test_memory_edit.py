"""A memory record is rewritten by a command, not through the projection and back.

THE GAP THIS CLOSES. The project's rule is that a record whose reference rotted but whose CLAIM is
still true gets REWRITTEN rather than deleted. The CLI offered `delete` and `supersede` and nothing
else, so sixteen corrections in one sweep went through the git projection and `state import`. That
path is declared and it works, but a workaround standing in for a command is what the next person
copies.

IDENTITY IS THE POINT. The id, the slug and `created_at` do not move: this is the same record with
a corrected claim. A supersede chain would assert that the old text was a different fact, when what
happened is that one sentence in it was wrong.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from memory_edit import edit_memory  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True)
    service = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
    yield service
    service.be.close()


@pytest.fixture
def mid(svc):
    svc.memory_add("pattern", "Первая редакция", "Тело записи с ошибкой в одном предложении")
    return int(svc.be._q1("SELECT id FROM memory ORDER BY id DESC")["id"])


def test_the_record_keeps_its_identity(svc, mid):
    """The same row, a corrected claim — not a new record pretending to replace an old one."""
    before = svc.be.memory_get(mid)
    edit_memory(svc, mid, content="Тело записи с исправленным предложением")
    after = svc.be.memory_get(mid)
    assert after["id"] == before["id"]
    assert after["slug"] == before["slug"]
    assert after["created_at"] == before["created_at"]
    assert after["content"] != before["content"]


def test_only_what_is_given_changes(svc, mid):
    """Omitting a field keeps it: a rewrite of the body must not blank the title."""
    edit_memory(svc, mid, content="только тело")
    row = svc.be.memory_get(mid)
    assert row["title"] == "Первая редакция" and row["content"] == "только тело"
    edit_memory(svc, mid, title="только заголовок")
    row = svc.be.memory_get(mid)
    assert row["title"] == "только заголовок" and row["content"] == "только тело"


def test_updated_at_moves_but_created_at_does_not(svc, mid):
    before = svc.be.memory_get(mid)
    edit_memory(svc, mid, title="новое имя")
    after = svc.be.memory_get(mid)
    assert after["created_at"] == before["created_at"]
    assert after["updated_at"] >= before["updated_at"]


#: What the command must refuse, and why each refusal is not pedantry.
_REFUSALS = (
    ("", None, "a rewrite that empties the title is a delete under another name"),
    (None, "   ", "same for the body — `memory delete` exists for that"),
)


@pytest.mark.parametrize("title,content,why", _REFUSALS)
def test_an_emptying_rewrite_is_refused(svc, mid, title, content, why):
    with pytest.raises(ServiceError, match="delete"):
        edit_memory(svc, mid, title=title, content=content)
    assert svc.be.memory_get(mid)["title"] == "Первая редакция", why


def test_an_archived_record_is_not_quietly_revived(svc, mid):
    """NEGATIVE: archiving was a decision, and editing past it would undo it silently."""
    svc.be.memory_archive_ids([mid])
    with pytest.raises(ServiceError, match="archived"):
        edit_memory(svc, mid, title="воскрешение")


def test_a_missing_record_says_so(svc):
    with pytest.raises(ServiceError, match="not found"):
        edit_memory(svc, 999_999, title="x")


def test_an_identical_rewrite_is_a_no_op(svc, mid):
    """Saying nothing new must not stamp `updated_at` — a projection that churns on a no-op
    makes every reader wonder what changed."""
    before = svc.be.memory_get(mid)
    msg = edit_memory(svc, mid, title=before["title"], content=before["content"])
    assert "unchanged" in msg
    assert svc.be.memory_get(mid)["updated_at"] == before["updated_at"]
