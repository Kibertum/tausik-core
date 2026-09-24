"""An existing project record reaches the shared store without being typed again,
and only on an explicit act (the-shared-store-has-no-promotion-path)."""

from __future__ import annotations

import os
import re
import sqlite3
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from brain_universality import format_universality_hint  # noqa: E402
from knowledge_promote import preview, promote  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_cli_extra import cmd_knowledge  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "p.db")))
    yield s
    s.be.close()


def _shared_rows(table):
    from knowledge_db import knowledge_db_path

    conn = sqlite3.connect(knowledge_db_path())
    try:
        return conn.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        conn.close()


def _mid(msg):
    return int(re.search(r"#(\d+)", msg).group(1))


def test_the_preview_shows_everything_that_leaves_and_the_warning(svc):
    mid = _mid(
        svc.memory_add("gotcha", "Ansible copy is bytewise", "line one\nline two", ["ansible"])
    )
    text = "\n".join(preview(svc, "memory", mid))
    assert "line one" in text and "line two" in text and "ansible" in text
    assert "NOT redacted" in text


def test_without_yes_nothing_is_written(svc, capsys):
    mid = _mid(svc.memory_add("gotcha", "G", "general fact"))
    cmd_knowledge(
        svc, SimpleNamespace(knowledge_cmd="promote", memory=mid, decision=None, yes=False)
    )
    assert "Nothing written" in capsys.readouterr().out
    from knowledge_db import knowledge_db_path

    assert not os.path.exists(knowledge_db_path()) or not _shared_rows("memory")


def test_promote_copies_with_provenance_and_leaves_the_local_record(svc):
    mid = _mid(svc.memory_add("gotcha", "G", "general fact"))
    slug = svc.be.memory_get(mid)["slug"]
    assert "SHARED store" in promote(svc, "memory", mid)
    rows = _shared_rows("memory")
    assert len(rows) == 1 and slug in rows[0]
    assert svc.be.memory_get(mid)["content"] == "general fact"


def test_a_decision_is_promoted_too(svc):
    did = _mid(svc.decide("Prefer stdlib", rationale="no deps"))
    assert "SHARED store" in promote(svc, "decision", did)
    assert len(_shared_rows("decisions")) == 1


def test_the_same_record_is_not_copied_twice(svc):
    mid = _mid(svc.memory_add("gotcha", "G", "general fact"))
    promote(svc, "memory", mid)
    with pytest.raises(ServiceError, match="already in the shared store"):
        promote(svc, "memory", mid)
    assert len(_shared_rows("memory")) == 1


def test_a_missing_record_is_refused(svc):
    with pytest.raises(ServiceError, match="not found"):
        promote(svc, "memory", 999)


def test_the_hint_names_the_command_and_writes_nothing():
    hint = format_universality_hint(["git"], promote="--memory 7")
    assert "tausik knowledge promote --memory 7" in hint and "--yes" in hint
