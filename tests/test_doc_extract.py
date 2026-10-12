"""Tests for scripts/doc_extract.py — optional markitdown wrapper."""

from __future__ import annotations

import os
import sys
import types

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import doc_extract  # noqa: E402


# --- Fakes ----------------------------------------------------------------


class _FakeResult:
    def __init__(self, text: str):
        self.text_content = text


class _FakeMarkItDown:
    def __init__(self):
        self.calls: list[str] = []

    def convert(self, path: str):
        self.calls.append(path)
        return _FakeResult(f"# Converted\n\n{os.path.basename(path)}")


def _install_fake_markitdown(monkeypatch, cls=None):
    """Patch sys.modules['markitdown'] with a fake module exposing MarkItDown."""
    fake = types.ModuleType("markitdown")
    fake.MarkItDown = cls or _FakeMarkItDown  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "markitdown", fake)


def _uninstall_markitdown(monkeypatch):
    """Make `import markitdown` fail."""
    monkeypatch.delitem(sys.modules, "markitdown", raising=False)
    # Block re-import by inserting None
    monkeypatch.setitem(sys.modules, "markitdown", None)


# --- is_available ---------------------------------------------------------


def test_is_available_when_installed(monkeypatch):
    _install_fake_markitdown(monkeypatch)
    assert doc_extract.is_available() is True


def test_is_available_when_missing(monkeypatch):
    _uninstall_markitdown(monkeypatch)
    assert doc_extract.is_available() is False


# --- extract_to_markdown happy path ---------------------------------------


def test_happy_path_returns_markdown(monkeypatch, tmp_path):
    _install_fake_markitdown(monkeypatch)
    f = tmp_path / "doc.docx"
    f.write_bytes(b"placeholder")
    out = doc_extract.extract_to_markdown(str(f))
    assert out is not None
    assert "Converted" in out
    assert "doc.docx" in out


def test_format_hint_logged_but_not_enforced(monkeypatch, tmp_path, capsys):
    _install_fake_markitdown(monkeypatch)
    f = tmp_path / "x.html"
    f.write_text("<html/>")
    out = doc_extract.extract_to_markdown(str(f), format_hint="html")
    assert out is not None
    captured = capsys.readouterr()
    assert "format_hint='html'" in captured.err


def test_falls_back_to_markdown_attr(monkeypatch, tmp_path):
    """Older markitdown versions exposed `.markdown`; newer use `.text_content`."""

    class _OldMD:
        def convert(self, path: str):
            return types.SimpleNamespace(
                markdown=f"old shape for {os.path.basename(path)}"
            )

    _install_fake_markitdown(monkeypatch, cls=_OldMD)
    f = tmp_path / "y.txt"
    f.write_text("x")
    out = doc_extract.extract_to_markdown(str(f))
    assert out is not None
    assert "old shape" in out


# --- Negative paths -------------------------------------------------------


def test_returns_none_when_markitdown_missing(monkeypatch, tmp_path, capsys):
    _uninstall_markitdown(monkeypatch)
    f = tmp_path / "doc.docx"
    f.write_bytes(b"x")
    out = doc_extract.extract_to_markdown(str(f))
    assert out is None
    captured = capsys.readouterr()
    assert "markitdown not installed" in captured.err


def test_returns_none_when_path_missing(monkeypatch, tmp_path, capsys):
    _install_fake_markitdown(monkeypatch)
    out = doc_extract.extract_to_markdown(str(tmp_path / "absent.pdf"))
    assert out is None
    captured = capsys.readouterr()
    assert "file not found" in captured.err


def test_returns_none_on_empty_path(monkeypatch, capsys):
    out = doc_extract.extract_to_markdown("")
    assert out is None
    captured = capsys.readouterr()
    assert "path is empty" in captured.err


def test_returns_none_when_markitdown_raises(monkeypatch, tmp_path, capsys):
    class _BoomMD:
        def convert(self, path: str):
            raise RuntimeError("corrupt file")

    _install_fake_markitdown(monkeypatch, cls=_BoomMD)
    f = tmp_path / "bad.pptx"
    f.write_bytes(b"corrupt")
    out = doc_extract.extract_to_markdown(str(f))
    assert out is None
    captured = capsys.readouterr()
    assert "markitdown failed" in captured.err
    assert "corrupt file" in captured.err


def test_returns_none_on_unexpected_result_shape(monkeypatch, tmp_path, capsys):
    """If markitdown returns something with neither attr, refuse cleanly."""

    class _WeirdMD:
        def convert(self, path: str):
            return object()  # no .text_content, no .markdown

    _install_fake_markitdown(monkeypatch, cls=_WeirdMD)
    f = tmp_path / "weird.bin"
    f.write_bytes(b"x")
    out = doc_extract.extract_to_markdown(str(f))
    assert out is None
    captured = capsys.readouterr()
    assert "unexpected" in captured.err


def test_non_string_path(monkeypatch):
    out = doc_extract.extract_to_markdown(None)  # type: ignore[arg-type]
    assert out is None


@pytest.mark.skipif(
    not doc_extract.is_available(),
    reason="markitdown not installed; integration-style test only runs when present",
)
def test_real_markitdown_on_text_file(tmp_path):
    """Soft integration test — only runs if markitdown is actually installed."""
    f = tmp_path / "hello.txt"
    f.write_text("hello world")
    out = doc_extract.extract_to_markdown(str(f))
    assert out is not None
    assert "hello world" in out
