#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit outside the active task's declared scope.

v15-scope-enforce-write (SENAR Rule 2, Walko ACL pattern): when every
active task declares `scope_paths`, a Write/Edit/MultiEdit whose target
falls outside the union of those ACLs is blocked (exit 2) with the
offending task, its ACL, and the remediation command.

Deliberately conservative adoption semantics:
  - no active task, or ANY active task without scope_paths -> allow
    (an undeclared task grants unrestricted writes — legacy behavior);
  - target outside the project root -> allow (auto-memory and other
    out-of-tree paths are governed by their own hooks);
  - pre-v30 DB (no scope_paths column) or any DB error -> fail-open,
    unless TAUSIK_HOOK_FAIL_SECURE=1 (same policy as task_gate.py).

Exit codes: 0 = allow, 2 = block. Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
sys.path.insert(1, os.path.dirname(_HOOKS_DIR))  # scripts/ — for scope_acl

from _common import is_tausik_project  # noqa: E402

_GATED_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def _read_stdin_json() -> dict:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _relative_to_project(file_path: str, project_dir: str) -> str | None:
    """Project-relative path, or None when the target is outside the root."""
    try:
        target = os.path.realpath(os.path.expanduser(file_path))
        root = os.path.realpath(project_dir)
        rel = os.path.relpath(target, root)
    except (OSError, ValueError):
        return None
    if rel == ".." or rel.startswith(".." + os.sep):
        return None
    return rel


def _active_acls(db_path: str) -> list[tuple[str, str | None]]:
    """[(slug, scope_paths_json), ...] for all active tasks.

    Raises sqlite3.Error for the caller's fail-open/fail-secure policy.
    A pre-v30 schema (no scope_paths column) surfaces as OperationalError.
    """
    conn = sqlite3.connect(db_path, timeout=2.0)
    try:
        rows = conn.execute(
            "SELECT slug, scope_paths FROM tasks WHERE status = 'active'"
        ).fetchall()
        return [(r[0], r[1]) for r in rows]
    finally:
        conn.close()


def _delegated_slugs(db_path: str) -> set[str]:
    """Slugs of tasks delegated to a worker sub-agent (meta delegation:<slug>).

    Best-effort: any error → empty set (the scope gate keeps its legacy policy).
    """
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        try:
            rows = conn.execute(
                "SELECT key, value FROM meta WHERE key LIKE 'delegation:%'"
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as e:
        # Don't fully swallow: a silent no-op here downgrades the delegated
        # hard-gate without any signal. Warn, then keep the legacy-empty policy.
        print(f"  scope-gate: delegation lookup failed ({e}); hard-gate inactive", file=sys.stderr)
        return set()
    return {key.split(":", 1)[1] for key, value in rows if value}


def _scope_empty(raw: str | None) -> bool:
    """True when scope_paths is absent OR a parsed-empty list ('[]')."""
    if raw is None:
        return True
    return str(raw).strip() in ("", "[]", "null")


def delegated_missing_scope(acls: list[tuple[str, str | None]], delegated: set[str]) -> str | None:
    """Return the slug of a DELEGATED active task that declares no usable scope.

    A delegated worker must be scope-bounded — it does NOT get the legacy
    'undeclared task = unrestricted writes' freedom. A parsed-empty '[]' counts
    as missing (it would otherwise grant an empty ACL that blocks every edit).
    """
    for slug, raw in acls:
        if slug in delegated and _scope_empty(raw):
            return slug
    return None


def has_declared_scope(acls: list[tuple[str, str | None]]) -> bool:
    """True iff at least one active task carries a scope_paths value.

    A value that is present but parses empty ("[]", corrupt JSON) still
    counts as *declared* — the task said "these paths and no others", which
    is enforcement, not abstention. Only an absent (NULL) value is undeclared.
    """
    return any(raw is not None for _slug, raw in acls)


def declared_acls(acls: list[tuple[str, str | None]]) -> list[tuple[str, list[str]]]:
    """[(slug, patterns), ...] for the active tasks that declared a scope."""
    from scope_acl import _parse_list

    return [(slug, _parse_list(raw, "scope_paths")) for slug, raw in acls if raw is not None]


def scope_allows(rel: str, acls: list[tuple[str, str | None]]) -> bool:
    """True iff `rel` is inside the union of every declared task's ACL.

    l26-hook-contract-review AC3: enforcement is the union of DECLARED scopes.
    A co-active task that declared no scope contributes nothing here — it no
    longer nullifies a sibling's ACL by merely existing (the old '`any(raw is
    None)` -> allow everything' escape hatch). The caller applies the legacy
    freedom only when `has_declared_scope` is False (nobody declared anything).
    """
    from scope_acl import match_path

    for _slug, patterns in declared_acls(acls):
        if match_path(rel, patterns):
            return True
    return False


def main() -> int:
    # hook-stderr-encoding-locale-dependent: this hook's messages contain
    # non-ASCII, and their readability must not depend on how it was
    # launched. Local import: hooks/ is sys.path[0] only when run as a script.
    from _common import (
        emit_supervision_bypass,
        emit_supervision_degradation,
        force_utf8_io,
    )

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        emit_supervision_bypass(
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()), "skip_hooks", "scope_write_gate"
        )
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    if not is_tausik_project(project_dir):
        return 0
    db_path = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(db_path):
        return 0

    event = _read_stdin_json()
    if event.get("tool_name") not in _GATED_TOOLS:
        return 0
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    # NotebookEdit carries its target as `notebook_path`, not `file_path`
    # (l26-hook-contract-review AC: NotebookEdit was previously ungated).
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(file_path, str) or not file_path:
        return 0

    rel = _relative_to_project(file_path, project_dir)
    if rel is None:
        return 0  # outside the project root — not this hook's jurisdiction

    fail_secure = bool(os.environ.get("TAUSIK_HOOK_FAIL_SECURE"))
    try:
        acls = _active_acls(db_path)
    except sqlite3.Error as e:
        if fail_secure:
            print(
                f"BLOCKED: TAUSIK_HOOK_FAIL_SECURE=1 set, but scope gate could "
                f"not query .tausik/tausik.db: {e}.",
                file=sys.stderr,
            )
            return 2
        # fail-open: pre-v30 schema / transient DB issue. Count the silently
        # dropped scope check so the degradation is not invisible.
        emit_supervision_degradation(project_dir, "db_error", "scope_write_gate", str(e))
        return 0

    # Orchestrator-worker (v15-ow-scope-hardgate): a DELEGATED active task must be
    # scope-bounded — it does NOT inherit the legacy 'undeclared = unrestricted'
    # freedom, or a worker sub-agent could sprawl. Block edits until it declares
    # scope (checked before the fail-open below).
    offender = delegated_missing_scope(acls, _delegated_slugs(db_path))
    if offender is not None:
        print(
            f"BLOCKED: delegated task '{offender}' has no scope_paths — a worker "
            f"sub-agent must declare its writable surface before editing. "
            f"Set it: `tausik task update {offender} --scope-paths <paths>`, "
            f"or hand it back: `tausik task undelegate {offender}`.",
            file=sys.stderr,
        )
        return 2

    # l26-hook-contract-review AC3: legacy 'undeclared task = unrestricted'
    # freedom applies ONLY when NO active task declared a scope. Once ANY task
    # declares one, the union of declared ACLs is enforced and a co-active
    # undeclared task no longer reopens the escape (previously `any(raw is
    # None)` disabled the ACL globally — a scope-declaring task could be
    # nullified by an unrelated undeclared sibling, or by keeping one active
    # on purpose).
    if not acls or not has_declared_scope(acls):
        return 0  # no active task, or nobody declared a scope — legacy freedom

    if scope_allows(rel, acls):
        return 0

    declared = declared_acls(acls)
    acl_lines = "\n".join(f"  {slug}: {patterns}" for slug, patterns in declared)
    first_slug = declared[0][0]
    rel = rel.replace("\\", "/")
    print(
        f"BLOCKED: '{rel}' is outside the declared scope of the active task(s) "
        f"(SENAR Rule 2 scope enforcement).\n{acl_lines}\n"
        f"Options: extend the ACL — `tausik task update {first_slug} "
        f"--scope-paths <existing...> {rel}` (overwrites prior list), or "
        "reconsider whether this file belongs to the task.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
