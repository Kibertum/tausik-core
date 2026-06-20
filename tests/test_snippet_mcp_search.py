"""v15-snippet-mcp-search: ranked snippet search + tausik_snippet_search MCP tool."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from snippet_storage import add_snippet, search_snippets_ranked


def _backend(tmp_path):
    return SQLiteBackend(str(tmp_path / "tausik.db"))


def _add(be, *, h, lang, code, src="f.py", lines="1-3", occ=2.0):
    add_snippet(
        be._conn,
        code_hash=h,
        language=lang,
        code=code,
        source_file=src,
        source_lines=lines,
        taxonomy_kind="helper",
        fts_rank=occ,
    )


# --- AC1: ranked storage search ----------------------------------------------


class TestRankedSearch:
    def test_basic_match_envelope_shape(self, tmp_path):
        be = _backend(tmp_path)
        try:
            _add(be, h="h1", lang="python", code="def authenticate(u):\n    return token")
            res = search_snippets_ranked(be._conn, "authenticate")
            assert len(res) == 1
            r = res[0]
            assert set(r) == {
                "code",
                "source",
                "language",
                "occurrences",
                "line_count",
                "taxonomy_kind",
            }
            assert r["source"] == "f.py:1-3"
            assert r["language"] == "python"
            assert r["occurrences"] == 2
            assert r["line_count"] == 2
        finally:
            be.close()

    def test_ranked_by_occurrences_desc(self, tmp_path):
        be = _backend(tmp_path)
        try:
            _add(be, h="a", lang="python", code="def login():\n    return token", occ=2.0)
            _add(be, h="b", lang="python", code="def login():\n    validate(creds)", occ=5.0)
            res = search_snippets_ranked(be._conn, "login")
            assert [r["occurrences"] for r in res] == [5, 2]  # higher cluster first
        finally:
            be.close()

    def test_language_filter(self, tmp_path):
        be = _backend(tmp_path)
        try:
            _add(be, h="py", lang="python", code="def render():\n    pass\n    return 1")
            _add(be, h="js", lang="javascript", code="function render(){\n return 1\n}")
            res = search_snippets_ranked(be._conn, "render", language="python")
            assert len(res) == 1
            assert res[0]["language"] == "python"
        finally:
            be.close()

    def test_source_is_file_only_when_no_lines(self, tmp_path):
        be = _backend(tmp_path)
        try:
            add_snippet(
                be._conn,
                code_hash="nolines",
                language="python",
                code="def helper():\n    return 42",
                source_file="util.py",
                source_lines=None,
                fts_rank=1.0,
            )
            res = search_snippets_ranked(be._conn, "helper")
            assert res[0]["source"] == "util.py"
        finally:
            be.close()

    def test_limit_clamped(self, tmp_path):
        be = _backend(tmp_path)
        try:
            for i in range(5):
                _add(be, h=f"h{i}", lang="python", code=f"def fn{i}():\n    shared_token()")
            assert len(search_snippets_ranked(be._conn, "shared_token", limit=2)) == 2
            # huge limit is clamped, never raises
            assert len(search_snippets_ranked(be._conn, "shared_token", limit=10_000)) == 5
        finally:
            be.close()


# --- AC3: negative / robustness ----------------------------------------------


class TestNegative:
    def test_empty_query_returns_empty(self, tmp_path):
        be = _backend(tmp_path)
        try:
            _add(be, h="h1", lang="python", code="def f():\n    return token")
            assert search_snippets_ranked(be._conn, "") == []
            assert search_snippets_ranked(be._conn, "   ") == []
        finally:
            be.close()

    def test_unknown_language_yields_empty(self, tmp_path):
        be = _backend(tmp_path)
        try:
            _add(be, h="h1", lang="python", code="def f():\n    return token")
            assert search_snippets_ranked(be._conn, "token", language="cobol") == []
        finally:
            be.close()

    def test_fts_operator_chars_do_not_raise(self, tmp_path):
        be = _backend(tmp_path)
        try:
            _add(be, h="h1", lang="python", code='def f():\n    return "AND OR"')
            # Query with FTS operator tokens / quotes — phrase-quoted, must not raise
            # AND must return a list (no exception escapes).
            result = search_snippets_ranked(be._conn, 'AND OR "x')
            assert isinstance(result, list)
        finally:
            be.close()


# --- AC2: MCP tool registration + JSON envelope ------------------------------


def _import_mcp():
    mcp_dir = os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    sys.path.insert(0, mcp_dir)
    from handlers import handle_tool  # noqa: E402
    from tools import TOOLS  # noqa: E402

    return handle_tool, TOOLS


class TestMcpTool:
    def test_tool_registered_in_tools_list(self):
        _handle, tools = _import_mcp()
        names = [t["name"] for t in tools]
        assert "tausik_snippet_search" in names
        tool = next(t for t in tools if t["name"] == "tausik_snippet_search")
        assert tool["inputSchema"]["required"] == ["query"]

    def test_handler_returns_json_envelope(self, tmp_path):
        handle_tool, _tools = _import_mcp()
        from project_service import ProjectService

        be = _backend(tmp_path)
        try:
            _add(be, h="h1", lang="python", code="def authenticate(u):\n    return token")
            svc = ProjectService(be)
            out = handle_tool(svc, "tausik_snippet_search", {"query": "authenticate"})
            env = json.loads(out)
            assert env["query"] == "authenticate"
            assert env["count"] == 1
            assert env["results"][0]["language"] == "python"
        finally:
            be.close()

    def test_handler_empty_query_no_error(self, tmp_path):
        handle_tool, _tools = _import_mcp()
        from project_service import ProjectService

        be = _backend(tmp_path)
        try:
            svc = ProjectService(be)
            env = json.loads(handle_tool(svc, "tausik_snippet_search", {"query": ""}))
            assert env["count"] == 0 and env["results"] == []
        finally:
            be.close()

    def test_handler_non_numeric_limit_does_not_crash(self, tmp_path):
        # H1 review fix: a junk limit must fall back to default, never raise.
        handle_tool, _tools = _import_mcp()
        from project_service import ProjectService

        be = _backend(tmp_path)
        try:
            _add(be, h="h1", lang="python", code="def authenticate(u):\n    return token")
            svc = ProjectService(be)
            for bad in ("many", "", None, True, "12abc"):
                env = json.loads(
                    handle_tool(
                        svc, "tausik_snippet_search", {"query": "authenticate", "limit": bad}
                    )
                )
                assert env["count"] == 1  # default limit applied, no crash
        finally:
            be.close()
