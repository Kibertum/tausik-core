"""The RAG index forgets paths that no longer exist (rag-index-never-prunes-deleted-paths).

Measured in session #189: 62 of 3507 indexed paths did not exist, 56 of them
under agents/ — the directory renamed to harness/. `git diff --name-status`
prints a rename as `R100<TAB>old<TAB>new`; the reader split it once, so the
old path was never deleted and the new one was read as the path "old<TAB>new".
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_RAG = os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "codebase-rag")
sys.path.insert(0, os.path.abspath(_RAG))

import rag_indexer  # noqa: E402
from rag_store import RAGStore  # noqa: E402

BODY = "def brain_store_decision(x):\n    return x * 2\n\n\ndef other(y):\n    return y + 1\n"


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "proj"
    (root / "agents" / "brain").mkdir(parents=True)
    (root / "agents" / "brain" / "handlers.py").write_text(BODY, encoding="utf-8")
    (root / "keep.py").write_text(BODY.replace("brain_store_decision", "kept"), encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "one")
    store = RAGStore(str(tmp_path / "rag.db"))
    rag_indexer.index_full(str(root), store)
    yield root, store
    store.close()


def _paths(store, table):
    return {r[0] for r in store._conn.execute(f"SELECT DISTINCT file_path FROM {table}")}


def _commit(root, msg):
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", msg)


def test_a_rename_line_is_read_as_two_paths(repo):
    root, _ = repo
    _git(root, "mv", "agents", "harness")
    _commit(root, "rename")
    first = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    modified, deleted = rag_indexer._get_changed_files(str(root), first)
    assert deleted == ["agents/brain/handlers.py"]
    assert modified == ["harness/brain/handlers.py"]


def test_a_renamed_file_leaves_both_tables_and_the_new_one_is_indexed(repo):
    root, store = repo
    _git(root, "mv", "agents", "harness")
    _commit(root, "rename")
    rag_indexer.index_incremental(str(root), store)
    for table in ("rag_chunks", "fts_code"):
        paths = _paths(store, table)
        assert "agents/brain/handlers.py" not in paths
        assert "harness/brain/handlers.py" in paths
    hits = [r["file_path"] for r in store.search("brain_store_decision")]
    assert hits and all(os.path.exists(os.path.join(root, h)) for h in hits)


def test_a_path_already_dead_in_the_index_is_pruned_and_a_live_one_kept(repo):
    root, store = repo
    store.upsert_file("agents/cursor/ghost.py", rag_indexer.chunk_file(BODY, "python"))
    (root / "new.py").write_text(BODY, encoding="utf-8")
    _commit(root, "touch")
    out = rag_indexer.index_incremental(str(root), store)
    for table in ("rag_chunks", "fts_code"):
        paths = _paths(store, table)
        assert "agents/cursor/ghost.py" not in paths
        assert {"keep.py", "agents/brain/handlers.py", "new.py"} <= paths
    assert out.get("files_pruned") == 1
