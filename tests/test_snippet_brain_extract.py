"""v15-snippet-brain-integration: `snippet extract --scope brain` + auto-propose."""

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


# --- AC1: pattern-card construction + classifier taxonomy --------------------


class TestPatternCard:
    def test_card_fields_and_taxonomy(self):
        snip = {
            "code": "def login(u):\n    return token(u)",
            "language": "python",
            "source_file": "auth.py",
            "fts_rank": 4.0,
        }
        card = cli._snippet_to_pattern_card(snip)
        assert card["artifact_taxonomy_kind"] in {"snippet", "pattern"}
        assert "```python" in card["example"]
        assert "def login" in card["example"]
        assert card["stack"] == ["python"]
        assert "auth.py" in card["description"]


# --- AC1: extract publishes via store_record(category=patterns) --------------


class TestExtract:
    def test_extract_calls_store_record(self, tmp_path, monkeypatch, capsys):
        svc = _svc(tmp_path)
        try:
            sid = _seed(svc)
            captured = {}

            def fake_store(client, conn, category, fields, cfg, **kw):
                captured["category"] = category
                captured["fields"] = fields
                return {"status": "ok", "notion_page_id": "pg1", "source_project_hash": "x"}

            monkeypatch.setattr(
                "brain_runtime.open_brain_deps",
                lambda: (svc.be._conn, object(), {"enabled": True}),
            )
            monkeypatch.setattr("brain_mcp_write.store_record", fake_store)
            cli.cmd_snippet(svc, SimpleNamespace(snippet_cmd="extract", id=sid, scope="brain"))
            assert captured["category"] == "patterns"
            assert "artifact_taxonomy_kind" in captured["fields"]
            assert "pg1" in capsys.readouterr().out
        finally:
            svc.be.close()

    def test_brain_disabled_message_no_write(self, tmp_path, monkeypatch, capsys):
        svc = _svc(tmp_path)
        try:
            sid = _seed(svc)
            calls = []
            monkeypatch.setattr(
                "brain_runtime.open_brain_deps", lambda: (None, None, {"enabled": False})
            )
            monkeypatch.setattr(
                "brain_mcp_write.store_record",
                lambda *a, **k: calls.append(1) or {"status": "ok"},
            )
            cli.cmd_snippet(svc, SimpleNamespace(snippet_cmd="extract", id=sid, scope="brain"))
            assert "not configured" in capsys.readouterr().out.lower()
            assert calls == []  # never wrote
        finally:
            svc.be.close()

    def test_open_brain_deps_raises_friendly_message(self, tmp_path, monkeypatch, capsys):
        # H3 review fix: a raising open_brain_deps -> message, not a traceback.
        svc = _svc(tmp_path)
        try:
            sid = _seed(svc)

            def boom():
                raise RuntimeError("notion client init failed")

            monkeypatch.setattr("brain_runtime.open_brain_deps", boom)
            cli.cmd_snippet(svc, SimpleNamespace(snippet_cmd="extract", id=sid, scope="brain"))
            assert "brain error" in capsys.readouterr().err.lower()
        finally:
            svc.be.close()

    def test_missing_snippet_id(self, tmp_path, capsys):
        svc = _svc(tmp_path)
        try:
            cli.cmd_snippet(svc, SimpleNamespace(snippet_cmd="extract", id=999, scope="brain"))
            assert "not found" in capsys.readouterr().out.lower()
        finally:
            svc.be.close()

    def test_unsupported_scope(self, tmp_path, monkeypatch, capsys):
        """An unknown destination is refused, and the refusal lists the real ones.

        Asserts the INTENT rather than the sentence: `global` joined `brain` as a
        destination, so pinning the old wording would have made this test a
        tripwire on prose instead of on behaviour. What must hold is that an
        unknown scope writes nothing and that the message names every scope that
        would have worked — a refusal that hides the alternatives is how someone
        ends up guessing.
        """
        svc = _svc(tmp_path)
        try:
            sid = _seed(svc)
            cli.cmd_snippet(svc, SimpleNamespace(snippet_cmd="extract", id=sid, scope="local"))
            out = capsys.readouterr().out.lower()
            assert "unsupported scope 'local'" in out
            assert "--scope brain" in out
            assert "--scope global" in out
        finally:
            svc.be.close()

    def test_global_scope_copies_into_the_shared_store(self, tmp_path, monkeypatch, capsys):
        """The new destination, exercised through the CLI rather than the helper.

        `write_snippet` has its own unit coverage; what this pins is the WIRING —
        that `--scope global` reaches it at all, and that it does so without
        touching the Notion path (no network, no brain config required).
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


# --- AC2 + AC3: auto-propose threshold (opt-in) ------------------------------


class TestAutoPropose:
    def test_proposes_when_threshold_met(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "brain_config.load_brain",
            lambda *a, **k: {"enabled": True, "auto_propose_snippet_threshold": 3},
        )
        cli._maybe_propose_brain_extract([(1, 5), (2, 2), (3, 3)])
        out = capsys.readouterr().out
        assert "snippet extract 1 --scope brain" in out
        assert "snippet extract 3 --scope brain" in out
        assert "extract 2" not in out  # 2 occurrences < threshold 3

    def test_silent_when_threshold_unset(self, monkeypatch, capsys):
        monkeypatch.setattr("brain_config.load_brain", lambda *a, **k: {"enabled": True})
        cli._maybe_propose_brain_extract([(1, 99)])
        assert capsys.readouterr().out == ""

    def test_silent_when_brain_disabled(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "brain_config.load_brain",
            lambda *a, **k: {"enabled": False, "auto_propose_snippet_threshold": 1},
        )
        cli._maybe_propose_brain_extract([(1, 99)])
        assert capsys.readouterr().out == ""
