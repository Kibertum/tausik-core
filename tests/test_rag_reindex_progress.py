"""r14-rag-reindex-timeout: index_full progress + max_seconds soft limit."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RAG_DIR = ROOT / "agents" / "claude" / "mcp" / "codebase-rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))


class _FakeStore:
    def __init__(self):
        self.cleared = False
        self.upserts: list[tuple[str, list[dict]]] = []
        self.meta: dict[str, str] = {}

    def clear(self):
        self.cleared = True

    def upsert_file(self, path, chunks):
        self.upserts.append((path, list(chunks)))

    def set_meta(self, k, v):
        self.meta[k] = v

    def get_meta(self, k):
        return self.meta.get(k)


@pytest.fixture()
def fake_files(monkeypatch, tmp_path):
    files = []
    for i in range(250):
        p = tmp_path / f"file_{i}.py"
        p.write_text("def x():\n    return 1\n")
        files.append(
            {"path": str(p), "rel_path": f"file_{i}.py", "language": "python"}
        )

    import rag_indexer

    monkeypatch.setattr(rag_indexer, "get_file_list", lambda d: files)
    monkeypatch.setattr(
        rag_indexer, "chunk_file", lambda content, lang: [{"text": content}]
    )
    monkeypatch.setattr(rag_indexer, "_get_current_commit", lambda d: "abc1234")
    yield files


def test_index_full_emits_progress_to_stderr(fake_files, capsys):
    from rag_indexer import index_full

    store = _FakeStore()
    stats = index_full("/tmp/x", store, progress_every=100)
    captured = capsys.readouterr()
    assert "[rag] indexed 100/250" in captured.err
    assert "[rag] indexed 200/250" in captured.err
    assert stats["files_indexed"] == 250
    assert stats["files_total"] == 250
    assert stats["truncated"] is False


def test_index_full_max_seconds_truncates(fake_files, monkeypatch):
    from rag_indexer import index_full

    times = iter([0.0, 0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    monkeypatch.setattr("rag_indexer.time.time", lambda: next(times))

    store = _FakeStore()
    stats = index_full("/tmp/x", store, max_seconds=3, progress_every=0)
    assert stats["truncated"] is True
    assert stats["files_indexed"] < stats["files_total"]


def test_progress_every_zero_disables_logging(fake_files, capsys):
    from rag_indexer import index_full

    store = _FakeStore()
    index_full("/tmp/x", store, progress_every=0)
    captured = capsys.readouterr()
    assert "[rag] indexed" not in captured.err
