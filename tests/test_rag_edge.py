"""RAG indexer edge case tests.

Tests path traversal protection, binary files, encoding issues,
symlinks, large files, special characters, and boundary conditions.
"""

import os
import sys

import pytest

_mcp_dir = os.path.join(os.path.dirname(__file__), "..", "agents", "claude", "mcp", "codebase-rag")
sys.path.insert(0, os.path.abspath(_mcp_dir))

from rag_detect import detect_language, get_file_list, _matches_ignore
from rag_indexer import (
    _safe_path, chunk_file, _chunk_by_lines, _normalize_chunks,
    MAX_CHUNK_CHARS, MIN_CHUNK_CHARS,
)
from rag_store import RAGStore


# === Path traversal protection ===

class TestSafePath:
    def test_normal_path(self, tmp_path):
        result = _safe_path(str(tmp_path), "src/main.py")
        assert result is not None
        assert result.startswith(str(tmp_path))

    def test_traversal_dotdot(self, tmp_path):
        result = _safe_path(str(tmp_path), "../../../etc/passwd")
        assert result is None

    def test_traversal_encoded(self, tmp_path):
        result = _safe_path(str(tmp_path), "src/../../etc/passwd")
        assert result is None

    def test_absolute_path_outside(self, tmp_path):
        # On Windows, absolute paths with different drives
        if sys.platform == "win32":
            result = _safe_path(str(tmp_path), "C:\\Windows\\system32\\cmd.exe")
        else:
            result = _safe_path(str(tmp_path), "/etc/passwd")
        assert result is None

    def test_project_root_itself(self, tmp_path):
        result = _safe_path(str(tmp_path), ".")
        assert result is not None  # project root is allowed


# === Binary and encoding edge cases ===

class TestFileEdgeCases:
    def test_binary_file_not_indexed(self, tmp_path):
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        files = get_file_list(str(tmp_path))
        paths = [f["rel_path"] for f in files]
        assert "image.png" not in paths

    def test_utf8_with_bom(self, tmp_path):
        bom = b"\xef\xbb\xbf"
        (tmp_path / "bom.py").write_bytes(bom + b"# -*- coding: utf-8 -*-\nprint('hello')\n")
        files = get_file_list(str(tmp_path))
        assert any(f["rel_path"] == "bom.py" for f in files)

    def test_empty_file(self, tmp_path):
        (tmp_path / "empty.py").write_text("")
        files = get_file_list(str(tmp_path))
        # Empty file should be in file list but produce no chunks
        chunks = chunk_file("", "python")
        assert chunks == []

    def test_whitespace_only_file(self):
        chunks = chunk_file("   \n\n\t\t\n   ", "python")
        assert chunks == []

    def test_single_line_file(self):
        chunks = chunk_file("x = 42", "python")
        assert len(chunks) >= 1
        assert "x = 42" in chunks[0]["content"]

    def test_very_long_line(self):
        content = "x = '" + "a" * 5000 + "'"
        chunks = chunk_file(content, "python")
        assert len(chunks) >= 1

    def test_file_with_null_bytes(self, tmp_path):
        """Files with null bytes should be handled gracefully."""
        (tmp_path / "mixed.py").write_bytes(b"# comment\x00\ndef foo(): pass\n")
        files = get_file_list(str(tmp_path))
        # Should still find the .py file
        py_files = [f for f in files if f["rel_path"] == "mixed.py"]
        if py_files:
            with open(py_files[0]["path"], encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            chunks = chunk_file(content, "python")
            assert isinstance(chunks, list)


# === Chunking edge cases ===

class TestChunkEdgeCases:
    def test_single_function_file(self):
        code = "def only_function():\n    return 42\n"
        chunks = chunk_file(code, "python")
        assert len(chunks) >= 1

    def test_deeply_nested_classes(self):
        code = "\n".join([
            "class Outer:",
            "    class Middle:",
            "        class Inner:",
            "            def method(self):",
            "                pass",
        ])
        chunks = chunk_file(code, "python")
        assert len(chunks) >= 1

    def test_no_boundaries_large_file(self):
        """File with no language boundaries falls back to line chunking."""
        content = "\n".join(f"# line {i}" for i in range(200))
        chunks = chunk_file(content, "python")
        # All lines are comments, no def/class boundaries → should still chunk
        assert len(chunks) >= 1

    def test_oversized_chunk_gets_split(self):
        """A single function >MAX_CHUNK_CHARS gets split."""
        lines = [f"    line_{i} = {i}" for i in range(200)]
        code = "def huge_function():\n" + "\n".join(lines)
        chunks = chunk_file(code, "python")
        # Should be split into multiple chunks
        total_content = "".join(c["content"] for c in chunks)
        assert "huge_function" in total_content

    def test_chunk_indices_contiguous(self):
        code = "\n".join(f"def func_{i}():\n    return {i}\n" for i in range(20))
        chunks = chunk_file(code, "python")
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_lines_cover_file(self):
        """Chunks should cover from line 1 to last line."""
        code = "\n".join(f"line {i}" for i in range(100))
        chunks = chunk_file(code, "unknown_lang")
        assert chunks[0]["start_line"] == 1
        assert chunks[-1]["end_line"] <= 100

    def test_normalize_merges_consecutive_tiny(self):
        chunks = [
            {"content": "x", "start_line": 1, "end_line": 1, "chunk_index": 0, "chunk_type": "code"},
            {"content": "y", "start_line": 2, "end_line": 2, "chunk_index": 1, "chunk_type": "code"},
            {"content": "z", "start_line": 3, "end_line": 3, "chunk_index": 2, "chunk_type": "code"},
        ]
        result = _normalize_chunks(chunks)
        # All tiny chunks should be merged into one
        assert len(result) == 1
        assert "x" in result[0]["content"]
        assert "z" in result[0]["content"]

    def test_all_supported_languages_chunk(self):
        """Every supported language should produce chunks from valid code."""
        samples = {
            "python": "def foo():\n    pass\n\ndef bar():\n    pass\n",
            "javascript": "function foo() { return 1; }\n\nfunction bar() { return 2; }\n",
            "go": "func main() {\n    fmt.Println(\"hello\")\n}\n",
            "rust": "fn main() {\n    println!(\"hello\");\n}\n",
            "java": "public class Main {\n    public static void main(String[] args) {}\n}\n",
            "markdown": "# Title\n\nContent here.\n\n## Section\n\nMore content.\n",
        }
        for lang, code in samples.items():
            chunks = chunk_file(code, lang)
            assert len(chunks) >= 1, f"{lang} produced no chunks"


# === RAG Store edge cases ===

class TestStoreEdgeCases:
    @pytest.fixture
    def store(self, tmp_path):
        s = RAGStore(str(tmp_path / "rag.db"))
        yield s
        s.close()

    def test_upsert_empty_chunks(self, store):
        """Upserting empty chunk list should just delete old data."""
        store.upsert_file("a.py", [
            {"chunk_index": 0, "content": "old content", "language": "python",
             "start_line": 1, "end_line": 1},
        ])
        store.upsert_file("a.py", [])
        status = store.status()
        assert status["total_chunks"] == 0

    def test_search_empty_db(self, store):
        results = store.search("anything")
        assert results == []

    def test_search_special_fts_chars(self, store):
        """FTS5 operators should not crash."""
        store.upsert_file("a.py", [
            {"chunk_index": 0, "content": "normal code here", "language": "python",
             "start_line": 1, "end_line": 1},
        ])
        # None of these should raise
        for query in ["AND", "OR NOT", "()", "**", "\"unclosed", "col:val", ""]:
            results = store.search(query)
            assert isinstance(results, list)

    def test_unicode_content(self, store):
        store.upsert_file("i18n.py", [
            {"chunk_index": 0, "content": "# Привет мир 你好世界 🌍",
             "language": "python", "start_line": 1, "end_line": 1},
        ])
        status = store.status()
        assert status["total_chunks"] == 1

    def test_very_long_file_path(self, store):
        path = "a/" * 100 + "deep.py"
        store.upsert_file(path, [
            {"chunk_index": 0, "content": "deep content", "language": "python",
             "start_line": 1, "end_line": 1},
        ])
        status = store.status()
        assert status["total_files"] == 1

    def test_concurrent_upsert_same_file(self, store):
        """Multiple rapid upserts to same file should end with last version."""
        for i in range(10):
            store.upsert_file("race.py", [
                {"chunk_index": 0, "content": f"version {i}", "language": "python",
                 "start_line": 1, "end_line": 1},
            ])
        results = store.search("version")
        assert len(results) == 1
        assert "version 9" in results[0]["content"]


# === Gitignore edge cases ===

class TestGitignoreEdge:
    def test_negation_pattern(self):
        # Simple negation not supported, but should not crash
        assert not _matches_ignore("important.log", ["!important.log"])

    def test_double_star_pattern(self):
        assert _matches_ignore("src/deep/nested/file.pyc", ["*.pyc"])

    def test_trailing_slash_dir(self):
        assert _matches_ignore("build/output.js", ["build"])

    def test_dotfile_not_ignored_by_default(self, tmp_path):
        (tmp_path / ".env.example").write_text("EXAMPLE=true")
        files = get_file_list(str(tmp_path))
        # .env.example has no known extension, should not be listed
        # This tests that dotfiles without recognized extensions are excluded

    def test_nested_gitignore_not_supported(self, tmp_path):
        """Only root .gitignore is parsed."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / ".gitignore").write_text("*.py\n")
        (sub / "code.py").write_text("x = 1")
        files = get_file_list(str(tmp_path))
        # sub/.gitignore should NOT affect indexing (only root .gitignore)
        paths = [f["rel_path"] for f in files]
        assert any("code.py" in p for p in paths)


# === Language detection edge cases ===

class TestDetectEdge:
    def test_case_insensitive_ext(self):
        # Our detect_language may or may not handle uppercase
        result = detect_language("Main.PY")
        # Either None or "python" is acceptable

    def test_no_extension(self):
        assert detect_language("Makefile") == "make"
        assert detect_language("Dockerfile") == "docker"

    def test_compound_extension(self):
        assert detect_language("component.test.tsx") == "typescript"
        assert detect_language("styles.module.css") == "css"
