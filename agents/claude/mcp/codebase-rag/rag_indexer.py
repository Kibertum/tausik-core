"""TAUSIK RAG — code indexer with smart chunking.

Reads project files, splits into chunks by language-aware boundaries,
stores in RAGStore. Supports full and incremental (git-based) indexing.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from typing import Any

from rag_detect import get_file_list, detect_language


def _safe_path(project_dir: str, rel_path: str) -> str | None:
    """Resolve path and verify it stays within project_dir. Returns full path or None."""
    # Normalize backslashes to forward slashes before joining (Windows traversal on Linux)
    rel_path = rel_path.replace("\\", "/")
    full = os.path.normpath(os.path.join(project_dir, rel_path))
    project_root = os.path.normpath(project_dir)
    if not full.startswith(project_root + os.sep) and full != project_root:
        return None
    return full


# Max chunk size in chars (fits embedding context windows)
MAX_CHUNK_CHARS = 4000
# Overlap lines between chunks for context continuity
OVERLAP_LINES = 5
# Min chunk size — don't create tiny chunks
MIN_CHUNK_CHARS = 50

# Language-specific top-level boundary patterns
_BOUNDARY_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^(class |def |async def )", re.MULTILINE),
    "javascript": re.compile(r"^(export |function |class |const \w+ = )", re.MULTILINE),
    "typescript": re.compile(
        r"^(export |function |class |interface |type |const \w+ = )", re.MULTILINE
    ),
    "go": re.compile(r"^(func |type )", re.MULTILINE),
    "rust": re.compile(r"^(pub |fn |impl |struct |enum |trait |mod )", re.MULTILINE),
    "java": re.compile(
        r"^(public |private |protected |class |interface )", re.MULTILINE
    ),
    "kotlin": re.compile(
        r"^(fun |class |interface |object |data class )", re.MULTILINE
    ),
    "ruby": re.compile(r"^(def |class |module )", re.MULTILINE),
    "php": re.compile(r"^(function |class |interface |trait )", re.MULTILINE),
    "csharp": re.compile(
        r"^(public |private |protected |class |interface |namespace )", re.MULTILINE
    ),
    "elixir": re.compile(r"^(def |defp |defmodule )", re.MULTILINE),
    "markdown": re.compile(r"^#{1,3} ", re.MULTILINE),
}


def chunk_file(content: str, language: str | None) -> list[dict[str, Any]]:
    """Split file content into indexable chunks.

    Uses language-aware boundaries when possible, falls back to line-based.
    Returns list of {content, start_line, end_line, chunk_index, chunk_type}.
    """
    if not content.strip():
        return []

    lines = content.split("\n")

    # Try language-aware splitting
    pattern = _BOUNDARY_PATTERNS.get(language or "") if language else None
    if pattern:
        chunks = _chunk_by_boundaries(lines, pattern)
    else:
        chunks = _chunk_by_lines(lines)

    # Post-process: merge tiny chunks, split oversized
    return _normalize_chunks(chunks)


def _chunk_by_boundaries(
    lines: list[str], pattern: re.Pattern[str]
) -> list[dict[str, Any]]:
    """Split at top-level code boundaries (functions, classes, etc.)."""
    boundaries: list[int] = []
    for i, line in enumerate(lines):
        if pattern.match(line):
            boundaries.append(i)

    if not boundaries:
        return _chunk_by_lines(lines)

    # Ensure we start from line 0
    if boundaries[0] != 0:
        boundaries.insert(0, 0)

    chunks = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        chunk_content = "\n".join(lines[start:end])
        if chunk_content.strip():
            chunks.append(
                {
                    "content": chunk_content,
                    "start_line": start + 1,
                    "end_line": end,
                    "chunk_index": idx,
                    "chunk_type": "code",
                }
            )
    return chunks


def _chunk_by_lines(lines: list[str], chunk_size: int = 80) -> list[dict[str, Any]]:
    """Fallback: split every N lines with overlap."""
    chunks = []
    idx = 0
    start = 0
    while start < len(lines):
        end = min(start + chunk_size, len(lines))
        chunk_content = "\n".join(lines[start:end])
        if chunk_content.strip():
            chunks.append(
                {
                    "content": chunk_content,
                    "start_line": start + 1,
                    "end_line": end,
                    "chunk_index": idx,
                    "chunk_type": "code",
                }
            )
        idx += 1
        start = end - OVERLAP_LINES if end < len(lines) else end
    return chunks


def _normalize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge tiny chunks, split oversized ones. Re-number chunk_index."""
    result: list[dict[str, Any]] = []
    buffer: dict[str, Any] | None = None

    for chunk in chunks:
        content = chunk["content"]

        # Merge tiny chunks into buffer
        if len(content) < MIN_CHUNK_CHARS:
            if buffer:
                buffer["content"] += "\n" + content
                buffer["end_line"] = chunk["end_line"]
            else:
                buffer = dict(chunk)
            continue

        # Flush buffer first
        if buffer:
            result.append(buffer)
            buffer = None

        # Split oversized chunks
        if len(content) > MAX_CHUNK_CHARS:
            lines = content.split("\n")
            sub_chunks = _chunk_by_lines(lines, chunk_size=60)
            for sc in sub_chunks:
                sc["start_line"] = chunk["start_line"] + sc["start_line"] - 1
                sc["end_line"] = chunk["start_line"] + sc["end_line"] - 1
                result.append(sc)
        else:
            result.append(chunk)

    if buffer:
        result.append(buffer)

    # Re-number
    for i, c in enumerate(result):
        c["chunk_index"] = i
    return result


def _get_current_commit(project_dir: str) -> str | None:
    """Get HEAD commit hash — reads .git directly to avoid subprocess hangs in MCP."""
    try:
        git_dir = os.path.join(project_dir, ".git")
        head_file = os.path.join(git_dir, "HEAD")
        if not os.path.isfile(head_file):
            return None
        with open(head_file, encoding="utf-8") as f:
            head = f.read().strip()
        # Resolve ref: refs/heads/main -> actual commit
        if head.startswith("ref: "):
            ref_path = os.path.join(git_dir, head[5:].replace("/", os.sep))
            if os.path.isfile(ref_path):
                with open(ref_path, encoding="utf-8") as f:
                    return f.read().strip()
            # Try packed-refs
            packed = os.path.join(git_dir, "packed-refs")
            if os.path.isfile(packed):
                ref_name = head[5:]
                with open(packed, encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("#"):
                            continue
                        parts = line.strip().split(" ", 1)
                        if len(parts) == 2 and parts[1] == ref_name:
                            return parts[0]
            return None
        # Detached HEAD — already a commit hash
        return head if len(head) == 40 else None
    except OSError:
        return None


def _get_changed_files(
    project_dir: str, since_commit: str
) -> tuple[list[str], list[str]]:
    """Get files changed since commit. Returns (modified, deleted)."""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-status", since_commit, "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if r.returncode != 0:
            return [], []
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return [], []

    modified, deleted = [], []
    for line in r.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, path = parts[0], parts[1]
        if status.startswith("D"):
            deleted.append(path)
        else:
            modified.append(path)
    return modified, deleted


def index_full(project_dir: str, store: Any) -> dict[str, Any]:
    """Full reindex: discover all files, chunk, store."""
    t0 = time.time()
    store.clear()

    files = get_file_list(project_dir)
    total_chunks = 0
    errors = 0

    for f in files:
        try:
            with open(f["path"], encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            chunks = chunk_file(content, f["language"])
            for c in chunks:
                c["language"] = f["language"]
            store.upsert_file(f["rel_path"], chunks)
            total_chunks += len(chunks)
        except OSError:
            errors += 1

    commit = _get_current_commit(project_dir)
    if commit:
        store.set_meta("last_commit", commit)
    store.set_meta("last_indexed", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    return {
        "files_indexed": len(files),
        "total_chunks": total_chunks,
        "errors": errors,
        "duration_sec": round(time.time() - t0, 2),
        "commit": commit,
    }


def index_incremental(project_dir: str, store: Any) -> dict[str, Any]:
    """Incremental reindex: only files changed since last commit."""
    last_commit = store.get_meta("last_commit")
    if not last_commit:
        return index_full(project_dir, store)

    current = _get_current_commit(project_dir)
    if current == last_commit:
        return {
            "files_indexed": 0,
            "total_chunks": 0,
            "message": "No changes since last index.",
        }

    t0 = time.time()
    modified, deleted = _get_changed_files(project_dir, last_commit)

    # Delete removed files from index
    for path in deleted:
        if _safe_path(project_dir, path) is None:
            continue  # path traversal — skip
        store.delete_file(path.replace("\\", "/"))

    # Re-index modified files
    total_chunks = 0
    indexed = 0
    for path in modified:
        full_path = _safe_path(project_dir, path)
        if not full_path:
            continue  # path traversal — skip
        rel_path = path.replace("\\", "/")
        if not os.path.exists(full_path):
            store.delete_file(rel_path)
            continue
        lang = detect_language(path)
        if not lang:
            continue
        try:
            with open(full_path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            chunks = chunk_file(content, lang)
            for c in chunks:
                c["language"] = lang
            store.upsert_file(rel_path, chunks)
            total_chunks += len(chunks)
            indexed += 1
        except OSError:
            continue

    if current:
        store.set_meta("last_commit", current)
    store.set_meta("last_indexed", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    return {
        "files_indexed": indexed,
        "files_deleted": len(deleted),
        "total_chunks": total_chunks,
        "duration_sec": round(time.time() - t0, 2),
        "commit": current,
    }
