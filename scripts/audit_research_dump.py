"""Audit docs/{en,ru}/research/ for stale retrospective dumps.

Finds files older than ``min_age_days`` (default 30) with NO active code
references in tests/, scripts/, or CHANGELOG.md/CHANGELOG.ru.md. Such
files are candidates to be moved into ``docs/_archive/research/`` to
reduce repo cognitive load and grep noise.

Read-only audit — never deletes or moves anything. Designed to replace
the manual `v14b-junk-research-archive` review by surfacing candidates
automatically when they ripen.

Public API:
    audit_research_dump(repo_root, min_age_days=30) -> dict
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Final

_RESEARCH_SUBDIRS: Final[tuple[str, ...]] = ("docs/en/research", "docs/ru/research")

_REF_SCAN_GLOBS: Final[tuple[str, ...]] = (
    "tests",
    "scripts",
    "CHANGELOG.md",
    "CHANGELOG.ru.md",
    "README.md",
    "README.ru.md",
)


def _list_research_files(repo_root: str) -> list[str]:
    out: list[str] = []
    for sub in _RESEARCH_SUBDIRS:
        d = os.path.join(repo_root, sub)
        if not os.path.isdir(d):
            continue
        for entry in sorted(os.listdir(d)):
            full = os.path.join(d, entry)
            if os.path.isfile(full) and entry.endswith(".md"):
                out.append(os.path.relpath(full, repo_root).replace("\\", "/"))
    return out


def _file_age_days(path: str) -> int:
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return 0
    age_sec = datetime.now(timezone.utc).timestamp() - mtime
    return max(0, int(age_sec // 86400))


def _has_references(repo_root: str, basename: str) -> bool:
    """Cheap text scan: does any file under _REF_SCAN_GLOBS mention this basename?"""
    needle = basename.encode("utf-8")
    for target in _REF_SCAN_GLOBS:
        full = os.path.join(repo_root, target)
        if os.path.isfile(full):
            try:
                with open(full, "rb") as fh:
                    if needle in fh.read():
                        return True
            except OSError:
                continue
        elif os.path.isdir(full):
            for root, _dirs, files in os.walk(full):
                for fname in files:
                    if not fname.endswith((".py", ".md", ".txt")):
                        continue
                    fp = os.path.join(root, fname)
                    try:
                        with open(fp, "rb") as fh:
                            if needle in fh.read():
                                return True
                    except OSError:
                        continue
    return False


def audit_research_dump(repo_root: str, min_age_days: int = 30) -> dict[str, Any]:
    """Find stale, unreferenced research files in docs/{en,ru}/research/.

    Returns:
        {
            "candidates": [{"path": str, "age_days": int}, ...],
            "skipped_recent": int,
            "skipped_referenced": int,
            "scanned": int,
        }
    """
    candidates: list[dict[str, Any]] = []
    skipped_recent = 0
    skipped_referenced = 0
    files = _list_research_files(repo_root)
    for rel in files:
        full = os.path.join(repo_root, rel)
        age = _file_age_days(full)
        if age < min_age_days:
            skipped_recent += 1
            continue
        basename = os.path.basename(rel)
        if _has_references(repo_root, basename):
            skipped_referenced += 1
            continue
        candidates.append({"path": rel, "age_days": age})
    return {
        "candidates": candidates,
        "skipped_recent": skipped_recent,
        "skipped_referenced": skipped_referenced,
        "scanned": len(files),
    }
