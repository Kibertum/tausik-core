"""`snippet extract` reaches the shared local store and refuses anything else.

The brain destination and the auto-propose nudge left with the Notion transport
(decision #358); what remains is the wiring to `knowledge_write.write_snippet`.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_cli_snippet as cli
from project_backend import SQLiteBackend
from project_service import ProjectService
from snippet_storage import add_snippet


def _svc(tmp_path):
    return ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))


def _seed(svc, *, code="def login(u):\n    return token(u)", lang="python", occ=4.0):
    return add_snippet(
        svc.be._conn,
        code_hash="h1",
        language=lang,
        code=code,
        source_file="auth.py",
        source_lines="10-12",
        taxonomy_kind="clone",
        fts_rank=occ,
    )


class TestExtract:
    def test_missing_snippet_id(self, tmp_path, capsys):
        svc = _svc(tmp_path)
        try:
            cli.cmd_snippet(svc, SimpleNamespace(snippet_cmd="extract", id=999, scope="global"))
            assert "not found" in capsys.readouterr().out.lower()
        finally:
            svc.be.close()

    def test_global_scope_copies_into_the_shared_store(self, tmp_path, monkeypatch, capsys):
        """The new destination, exercised through the CLI rather than the helper.

        `write_snippet` has its own unit coverage; what this pins is the WIRING —
        that `--scope global` reaches it at all, with no network and no config.
        """
        monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
        import knowledge_db

        svc = _svc(tmp_path)
        try:
            sid = _seed(svc)
            cli.cmd_snippet(svc, SimpleNamespace(snippet_cmd="extract", id=sid, scope="global"))
            assert "shared store" in capsys.readouterr().out.lower()
        finally:
            svc.be.close()

        conn = knowledge_db.connect_knowledge_db(create=False)
        assert conn is not None, "the shared store was never created"
        try:
            assert conn.execute("SELECT COUNT(*) FROM snippets").fetchone()[0] == 1
        finally:
            conn.close()
