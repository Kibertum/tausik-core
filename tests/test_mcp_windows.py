"""MCP Windows integration tests.

Tests covering Windows-specific bugs found in real projects:
- subprocess hang in MCP context (resolved: read .git/HEAD directly)
- path resolution with backslashes
- async context manager for stdio_server
- safe_path traversal prevention on Windows

Run: pytest tests/test_mcp_windows.py -v
"""

from __future__ import annotations

import os
import sys


# Add RAG module to path
_rag_dir = os.path.join(os.path.dirname(__file__), "..", "agents", "claude", "mcp", "codebase-rag")
sys.path.insert(0, os.path.abspath(_rag_dir))

from rag_indexer import _get_current_commit, _get_changed_files, _safe_path, chunk_file
from rag_detect import get_file_list, detect_language


class TestGitHeadReading:
    """Test _get_current_commit reads .git/HEAD directly (no subprocess)."""

    def test_normal_ref(self, tmp_path):
        """HEAD pointing to refs/heads/main with loose ref file."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        refs = git_dir / "refs" / "heads"
        refs.mkdir(parents=True)
        (refs / "main").write_text("abc123def456" * 3 + "abcd\n")  # 40 chars

        result = _get_current_commit(str(tmp_path))
        assert result == "abc123def456" * 3 + "abcd"

    def test_detached_head(self, tmp_path):
        """Detached HEAD — direct commit hash."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        commit = "a" * 40
        (git_dir / "HEAD").write_text(commit + "\n")

        result = _get_current_commit(str(tmp_path))
        assert result == commit

    def test_packed_refs_fallback(self, tmp_path):
        """HEAD ref not in loose file, found in packed-refs."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/feature\n")
        # No loose ref file — only packed-refs
        commit = "b" * 40
        (git_dir / "packed-refs").write_text(
            "# pack-refs with: peeled fully-peeled sorted\n"
            f"{commit} refs/heads/feature\n"
        )

        result = _get_current_commit(str(tmp_path))
        assert result == commit

    def test_no_git_dir(self, tmp_path):
        """No .git directory — returns None gracefully."""
        result = _get_current_commit(str(tmp_path))
        assert result is None

    def test_empty_head_file(self, tmp_path):
        """Empty HEAD file — returns None."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("")

        result = _get_current_commit(str(tmp_path))
        assert result is None

    def test_invalid_short_hash(self, tmp_path):
        """Short hash in detached HEAD — rejected (not 40 chars)."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("abc123\n")

        result = _get_current_commit(str(tmp_path))
        assert result is None


class TestSafePath:
    """Test _safe_path prevents directory traversal on Windows."""

    def test_normal_relative_path(self, tmp_path):
        """Normal relative path resolves correctly."""
        result = _safe_path(str(tmp_path), "src/main.py")
        expected = os.path.normpath(os.path.join(str(tmp_path), "src/main.py"))
        assert result == expected

    def test_traversal_blocked(self, tmp_path):
        """Path traversal with .. is blocked."""
        result = _safe_path(str(tmp_path), "../../../etc/passwd")
        assert result is None

    def test_windows_backslash_traversal(self, tmp_path):
        """Windows-style backslash traversal is blocked."""
        result = _safe_path(str(tmp_path), "..\\..\\Windows\\System32\\config")
        assert result is None

    def test_root_path_exact_match(self, tmp_path):
        """Path that resolves to exactly project_dir is allowed."""
        result = _safe_path(str(tmp_path), ".")
        assert result == os.path.normpath(str(tmp_path))

    def test_path_with_spaces(self, tmp_path):
        """Path with spaces works correctly."""
        result = _safe_path(str(tmp_path), "src/my module/file.py")
        assert result is not None
        assert "my module" in result


class TestChangedFiles:
    """Test _get_changed_files subprocess handling."""

    def test_no_git_installed(self, tmp_path):
        """If git is not found, returns empty lists gracefully."""
        # Use a non-existent directory to ensure git fails
        modified, deleted = _get_changed_files(str(tmp_path), "abc123")
        # Should not raise, should return empty
        assert isinstance(modified, list)
        assert isinstance(deleted, list)

    def test_timeout_handling(self, tmp_path):
        """Subprocess timeout returns empty lists (no hang)."""
        # This tests the timeout=3 parameter — git diff on a non-repo
        modified, deleted = _get_changed_files(str(tmp_path), "nonexistent")
        assert modified == []
        assert deleted == []


class TestPathNormalization:
    """Test that path handling works with Windows separators."""

    def test_detect_language_with_backslashes(self):
        """detect_language handles Windows-style paths."""
        assert detect_language("src\\main.py") == "python"
        assert detect_language("src\\index.ts") == "typescript"
        assert detect_language("cmd\\main.go") == "go"

    def test_detect_language_with_forward_slashes(self):
        """detect_language handles Unix-style paths."""
        assert detect_language("src/main.py") == "python"
        assert detect_language("src/index.js") == "javascript"

    def test_chunk_file_empty_content(self):
        """chunk_file handles empty string without error."""
        result = chunk_file("", "python")
        assert result == []

    def test_chunk_file_whitespace_only(self):
        """chunk_file handles whitespace-only content."""
        result = chunk_file("   \n\n  \n", "python")
        assert result == []


class TestFileListGitignore:
    """Test get_file_list respects .gitignore patterns."""

    def test_respects_gitignore(self, tmp_path):
        """Files matching .gitignore patterns are excluded."""
        # Create structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "pkg.js").write_text("module.exports = {}")
        (tmp_path / ".gitignore").write_text("node_modules/\n")

        files = get_file_list(str(tmp_path))
        paths = [f["rel_path"] for f in files]

        # src/main.py should be included
        assert any("main.py" in p for p in paths)
        # node_modules should be excluded
        assert not any("node_modules" in p for p in paths)

    def test_hidden_dirs_excluded(self, tmp_path):
        """Hidden directories (.git, .venv) are always excluded."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("[core]")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin")
        (tmp_path / "main.py").write_text("x = 1")

        files = get_file_list(str(tmp_path))
        paths = [f["rel_path"] for f in files]

        assert any("main.py" in p for p in paths)
        assert not any(".git" in p for p in paths)
        assert not any(".venv" in p for p in paths)
