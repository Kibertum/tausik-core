"""Tests for TAUSIK RAG — detect, store, indexer."""

import os
import sys
import textwrap

import pytest

# Add MCP source to path
_mcp_dir = os.path.join(
    os.path.dirname(__file__), "..", "agents", "claude", "mcp", "codebase-rag"
)
sys.path.insert(0, os.path.abspath(_mcp_dir))

from rag_detect import (
    detect_language,
    get_file_list,
    parse_gitignore,
    _matches_ignore,
)
from rag_indexer import chunk_file, _chunk_by_lines, _normalize_chunks
from rag_store import RAGStore


# ── Detection ──────────────────────────────────────────────


class TestDetectLanguage:
    def test_python(self):
        assert detect_language("foo.py") == "python"

    def test_typescript(self):
        assert detect_language("bar.tsx") == "typescript"

    def test_go(self):
        assert detect_language("main.go") == "go"

    def test_dockerfile(self):
        assert detect_language("Dockerfile") == "docker"

    def test_makefile(self):
        assert detect_language("Makefile") == "make"

    def test_unknown(self):
        assert detect_language("data.bin") is None

    def test_markdown(self):
        assert detect_language("README.md") == "markdown"


class TestGitignore:
    def test_parse_gitignore(self, tmp_path):
        gi = tmp_path / ".gitignore"
        gi.write_text("*.pyc\n# comment\n\nnode_modules/\n")
        patterns = parse_gitignore(str(tmp_path))
        assert "*.pyc" in patterns
        assert "node_modules" in patterns
        assert "# comment" not in patterns

    def test_no_gitignore(self, tmp_path):
        assert parse_gitignore(str(tmp_path)) == []

    def test_matches_simple(self):
        assert _matches_ignore("foo.pyc", ["*.pyc"])
        assert not _matches_ignore("foo.py", ["*.pyc"])

    def test_matches_dir(self):
        assert _matches_ignore("node_modules/foo.js", ["node_modules"])

    def test_matches_nested(self):
        assert _matches_ignore("src/dist/bundle.js", ["dist"])


class TestFileList:
    def test_finds_python_files(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "lib.py").write_text("x = 1")
        (tmp_path / "data.bin").write_bytes(b"\x00\x01")
        files = get_file_list(str(tmp_path))
        langs = [f["language"] for f in files]
        assert "python" in langs
        assert len(files) == 2  # only .py files

    def test_respects_gitignore(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n")
        (tmp_path / "app.py").write_text("x = 1")
        (tmp_path / "debug.log").write_text("log data")
        files = get_file_list(str(tmp_path))
        paths = [f["rel_path"] for f in files]
        assert "app.py" in paths
        assert "debug.log" not in paths

    def test_skips_always_ignored_dirs(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.js").write_text("module.exports = {}")
        (tmp_path / "app.js").write_text("console.log('hi')")
        files = get_file_list(str(tmp_path))
        paths = [f["rel_path"] for f in files]
        assert "app.js" in paths
        assert not any("node_modules" in p for p in paths)


# ── Chunking ───────────────────────────────────────────────


class TestChunking:
    def test_python_boundaries(self):
        # Need enough code per boundary to avoid merge of tiny chunks
        code = textwrap.dedent("""\
            import os
            import sys
            import json
            # module-level setup
            LOG = True

            def foo():
                '''Do foo things.'''
                x = 1
                y = 2
                return x + y

            def bar():
                '''Do bar things.'''
                a = 10
                b = 20
                return a * b

            class Baz:
                '''Baz class.'''
                def __init__(self):
                    self.val = 42
                def run(self):
                    return self.val
        """)
        chunks = chunk_file(code, "python")
        assert len(chunks) >= 3  # imports, foo, bar, Baz

    def test_empty_content(self):
        assert chunk_file("", "python") == []
        assert chunk_file("   \n\n  ", "python") == []

    def test_fallback_for_unknown_lang(self):
        content = "\n".join(f"line {i}" for i in range(200))
        chunks = chunk_file(content, "toml")
        assert len(chunks) >= 2  # should split into multiple

    def test_line_based_overlap(self):
        lines = [f"line {i}" for i in range(100)]
        chunks = _chunk_by_lines(lines, chunk_size=50)
        assert len(chunks) >= 2
        # Second chunk starts with overlap (before line 51)
        assert chunks[1]["start_line"] < 51

    def test_chunk_index_sequential(self):
        code = "\n".join(f"def func_{i}(): pass" for i in range(10))
        chunks = chunk_file(code, "python")
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_normalize_merges_tiny(self):
        chunks = [
            {
                "content": "x",
                "start_line": 1,
                "end_line": 1,
                "chunk_index": 0,
                "chunk_type": "code",
            },
            {
                "content": "y",
                "start_line": 2,
                "end_line": 2,
                "chunk_index": 1,
                "chunk_type": "code",
            },
        ]
        result = _normalize_chunks(chunks)
        assert len(result) == 1  # merged

    def test_markdown_headings(self):
        # Need enough content per section to avoid tiny-chunk merge
        sections = []
        for i in range(3):
            section = f"## Section {i}\n\n" + "\n".join(
                f"Paragraph {j} with some text content." for j in range(5)
            )
            sections.append(section)
        md = "# Title\n\nIntro paragraph with detail.\n\n" + "\n\n".join(sections)
        chunks = chunk_file(md, "markdown")
        assert len(chunks) >= 2


# ── Store ──────────────────────────────────────────────────


class TestRAGStore:
    @pytest.fixture
    def store(self, tmp_path):
        s = RAGStore(str(tmp_path / "rag.db"))
        yield s
        s.close()

    def test_upsert_and_search(self, store):
        chunks = [
            {
                "chunk_index": 0,
                "content": "def hello_world(): print('hi')",
                "language": "python",
                "start_line": 1,
                "end_line": 3,
            },
        ]
        store.upsert_file("main.py", chunks)
        results = store.search("hello_world")
        assert len(results) >= 1
        assert results[0]["file_path"] == "main.py"

    def test_upsert_replaces(self, store):
        chunks_v1 = [
            {
                "chunk_index": 0,
                "content": "old code alpha",
                "language": "python",
                "start_line": 1,
                "end_line": 1,
            }
        ]
        chunks_v2 = [
            {
                "chunk_index": 0,
                "content": "new code beta",
                "language": "python",
                "start_line": 1,
                "end_line": 1,
            }
        ]
        store.upsert_file("a.py", chunks_v1)
        store.upsert_file("a.py", chunks_v2)
        results = store.search("beta")
        assert len(results) == 1
        assert "new" in results[0]["content"]
        # Verify only 1 row in table (not duplicated)
        row = store._conn.execute(
            "SELECT COUNT(*) as c FROM rag_chunks WHERE file_path='a.py'"
        ).fetchone()
        assert row["c"] == 1

    def test_delete_file(self, store):
        store.upsert_file(
            "tmp.py",
            [
                {
                    "chunk_index": 0,
                    "content": "temporary data xyz123",
                    "language": "python",
                    "start_line": 1,
                    "end_line": 1,
                },
            ],
        )
        store.delete_file("tmp.py")
        results = store.search("xyz123")
        assert len(results) == 0

    def test_clear(self, store):
        store.upsert_file(
            "a.py",
            [
                {
                    "chunk_index": 0,
                    "content": "some content",
                    "language": "python",
                    "start_line": 1,
                    "end_line": 1,
                },
            ],
        )
        store.clear()
        status = store.status()
        assert status["total_chunks"] == 0
        assert status["total_files"] == 0

    def test_status(self, store):
        store.upsert_file(
            "a.py",
            [
                {
                    "chunk_index": 0,
                    "content": "code a",
                    "language": "python",
                    "start_line": 1,
                    "end_line": 5,
                },
            ],
        )
        store.upsert_file(
            "b.ts",
            [
                {
                    "chunk_index": 0,
                    "content": "code b",
                    "language": "typescript",
                    "start_line": 1,
                    "end_line": 5,
                },
            ],
        )
        status = store.status()
        assert status["total_chunks"] == 2
        assert status["total_files"] == 2
        assert status["mode"] == "fts5"
        assert "python" in status["languages"]

    def test_meta(self, store):
        store.set_meta("last_commit", "abc123")
        assert store.get_meta("last_commit") == "abc123"
        assert store.get_meta("nonexistent") is None

    def test_search_sanitization(self, store):
        """FTS5 special chars don't crash search."""
        store.upsert_file(
            "x.py",
            [
                {
                    "chunk_index": 0,
                    "content": "def test(): pass",
                    "language": "python",
                    "start_line": 1,
                    "end_line": 1,
                },
            ],
        )
        # These should not raise
        store.search("AND OR NOT")
        store.search("foo(bar)")
        store.search("")
        store.search("***")

    def test_fallback_search(self, store):
        store.upsert_file(
            "z.py",
            [
                {
                    "chunk_index": 0,
                    "content": "unique_marker_abc",
                    "language": "python",
                    "start_line": 1,
                    "end_line": 1,
                },
            ],
        )
        results = store._fallback_search("unique_marker_abc", 10)
        assert len(results) >= 1


# ── Integration ────────────────────────────────────────────


class TestIndexerIntegration:
    def test_full_index(self, tmp_path):
        # Create a mini project
        (tmp_path / "hello.py").write_text(
            "def greet(name):\n    return f'Hello {name}'\n"
        )
        (tmp_path / "utils.py").write_text(
            "MAX = 100\ndef clamp(x): return min(x, MAX)\n"
        )
        (tmp_path / "readme.md").write_text("# My Project\n\nA simple project.\n")
        (tmp_path / ".gitignore").write_text("*.pyc\n__pycache__/\n")
        (tmp_path / "ignored.pyc").write_bytes(b"\x00")

        from rag_indexer import index_full

        store = RAGStore(str(tmp_path / "rag.db"))
        stats = index_full(str(tmp_path), store)

        assert stats["files_indexed"] == 4  # .gitignore, hello.py, utils.py, readme.md
        assert stats["total_chunks"] > 0
        assert stats["errors"] == 0

        # Verify search works
        results = store.search("greet")
        assert any("greet" in r["content"] for r in results)

        store.close()
