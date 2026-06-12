"""Task scope ACL — declared allowed paths/tools (SENAR Rule 2).

v15-scope-declare: tasks carry two optional JSON-list columns,
`scope_paths` (glob patterns the task is allowed to write) and
`scope_tools` (tool names the task may use). This module owns the
canonical (de)serialization; enforcement lands separately
(v15-scope-enforce-write reads `parse_task_acl`).

Contract:
  - normalize_acl_json: strict — writers must declare a clean ACL or get
    a ValueError they can show the user.
  - parse_task_acl: lenient — readers (hooks, gates) must never crash on
    a corrupt DB row; bad JSON degrades to an empty ACL with a log line.
"""

from __future__ import annotations

import json
import logging
from typing import Any

_log = logging.getLogger("tausik.scope")

ACL_FIELDS = ("scope_paths", "scope_tools")


def normalize_acl_json(value: Any, field: str) -> str | None:
    """Canonical JSON for an ACL list; None clears the field.

    Accepts a list/tuple of strings (CLI nargs, MCP arrays) or a JSON
    string encoding one. Entries are stripped; empty entries, non-string
    entries and non-list shapes raise ValueError with the field name.
    An empty list is valid and stored as "[]" (explicit "nothing allowed").
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as e:
            raise ValueError(f"{field}: not valid JSON ({e})") from e
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field}: expected a JSON list of strings, got {type(value).__name__}")
    items: list[str] = []
    for i, entry in enumerate(value):
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError(f"{field}[{i}]: entries must be non-empty strings, got {entry!r}")
        items.append(entry.strip())
    return json.dumps(items, ensure_ascii=False)


def _parse_list(raw: Any, field: str) -> list[str]:
    if raw is None or raw == "":
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        _log.warning("scope ACL: corrupt %s JSON in DB row — treating as empty", field)
        return []
    if not isinstance(value, list):
        _log.warning("scope ACL: %s is not a list — treating as empty", field)
        return []
    return [str(v) for v in value if isinstance(v, str) and v.strip()]


def parse_task_acl(task: dict[str, Any]) -> dict[str, list[str]]:
    """Lenient reader: {"paths": [...], "tools": [...]}, empty on any defect."""
    return {
        "paths": _parse_list(task.get("scope_paths"), "scope_paths"),
        "tools": _parse_list(task.get("scope_tools"), "scope_tools"),
    }


def match_path(rel_path: str, patterns: list[str]) -> bool:
    """True iff `rel_path` (project-relative) is allowed by any pattern.

    Matching is '/'-normalized and case-insensitive (Windows paths):
      - "docs/"            -> directory prefix (anything under docs/)
      - "scripts/*.py"     -> fnmatch glob; NOTE: '*' crosses '/' (fnmatch
                              semantics), so this also matches subdirs
      - "scripts/file.py"  -> exact file, or directory prefix when the
                              entry names a directory without trailing '/'
    Empty pattern entries are ignored; empty list matches nothing.
    """
    import fnmatch

    def _norm(p: str) -> str:
        p = p.replace("\\", "/").strip().lower()
        return p[2:] if p.startswith("./") else p

    rp = _norm(rel_path)
    if not rp:
        return False
    for raw in patterns:
        p = _norm(raw)
        if not p:
            continue
        if p.endswith("/"):
            if rp.startswith(p):
                return True
        elif any(ch in p for ch in "*?["):
            if fnmatch.fnmatchcase(rp, p):
                return True
        elif rp == p or rp.startswith(p + "/"):
            return True
    return False
