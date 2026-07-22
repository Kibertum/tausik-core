"""Tests for scripts/hooks/scope_write_gate.py + scope_acl.match_path.

AC coverage (v15-scope-enforce-write): block outside ACL, allow inside /
legacy / out-of-tree, explicit-empty ACL blocks all, fail-open on broken
DB with TAUSIK_HOOK_FAIL_SECURE escalation, TAUSIK_SKIP_HOOKS skip.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys

import pytest
from conftest import canonical_ddl

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from scope_acl import match_path  # noqa: E402

HOOK = os.path.join(_SCRIPTS, "hooks", "scope_write_gate.py")


class TestMatchPath:
    @pytest.mark.parametrize(
        "rel,patterns,expected",
        [
            ("scripts/a.py", ["scripts/a.py"], True),
            ("scripts/a.py", ["scripts/b.py"], False),
            ("scripts/sub/a.py", ["scripts/*.py"], True),  # fnmatch '*' crosses '/'
            ("docs/ru/x.md", ["docs/"], True),
            ("docs2/x.md", ["docs/"], False),
            ("scripts/a.py", ["scripts"], True),  # bare dir name = prefix
            ("scripts.py", ["scripts"], False),
            ("tests/test_x.py", ["tests/*"], True),
            ("SCRIPTS/A.PY", ["scripts/a.py"], True),  # case-insensitive
            ("scripts\\a.py", ["scripts/a.py"], True),  # backslash normalized
            ("./scripts/a.py", ["scripts/a.py"], True),
            ("scripts/a.py", [], False),  # empty ACL matches nothing
            ("scripts/a.py", ["", "  "], False),
            ("", ["*"], False),
        ],
    )
    def test_semantics(self, rel, patterns, expected):
        assert match_path(rel, patterns) is expected


def _make_db(tmp_path, tasks):
    """tasks: [(slug, status, scope_paths_json_or_None)]"""
    tausik = tmp_path / ".tausik"
    tausik.mkdir(exist_ok=True)
    db = tausik / "tausik.db"
    conn = sqlite3.connect(str(db))
    conn.execute(canonical_ddl("tasks"))
    conn.executemany(
        # Поимённо, а не позиционно: на канонных 42 колонках позиционный
        # INSERT привязывался бы к их порядку и разъезжался бы молча.
        "INSERT INTO tasks (slug, title, status, scope_paths, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
        [(slug, slug, status, paths) for slug, status, paths in tasks],
    )
    conn.commit()
    conn.close()
    return str(db)


def _run_hook(project_dir, tool="Write", file_path=None, env_extra=None):
    env = os.environ.copy()
    env["TAUSIK_SKIP_HOOKS"] = ""
    env["TAUSIK_HOOK_FAIL_SECURE"] = ""
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    if env_extra:
        env.update(env_extra)
    payload = {"tool_name": tool, "tool_input": {"file_path": file_path}}
    return subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=10,
    )


class TestHook:
    def test_write_inside_scope_allowed(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", '["scripts/*.py"]')])
        r = _run_hook(tmp_path, file_path=str(tmp_path / "scripts" / "a.py"))
        assert r.returncode == 0, r.stderr

    def test_write_outside_scope_blocked(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", '["scripts/*.py"]')])
        r = _run_hook(tmp_path, file_path=str(tmp_path / "docs" / "x.md"))
        assert r.returncode == 2
        assert "BLOCKED" in r.stderr and "t1" in r.stderr and "--scope-paths" in r.stderr

    def test_explicit_empty_acl_blocks_everything(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", "[]")])
        r = _run_hook(tmp_path, file_path=str(tmp_path / "scripts" / "a.py"))
        assert r.returncode == 2

    def test_union_across_active_tasks(self, tmp_path):
        _make_db(
            tmp_path,
            [("t1", "active", '["scripts/"]'), ("t2", "active", '["docs/"]')],
        )
        assert _run_hook(tmp_path, file_path=str(tmp_path / "docs" / "x.md")).returncode == 0
        assert _run_hook(tmp_path, file_path=str(tmp_path / "other" / "x.md")).returncode == 2

    def test_undeclared_sibling_no_longer_reopens_scope(self, tmp_path):
        # l26-hook-contract-review AC3: once ANY active task declares a scope,
        # a co-active UNDECLARED task no longer nullifies it. Was the escape
        # hatch — keep one undeclared task active and the ACL vanished globally.
        _make_db(tmp_path, [("t1", "active", '["scripts/"]'), ("t2", "active", None)])
        # outside t1's scope -> now blocked (previously allowed via t2)
        assert _run_hook(tmp_path, file_path=str(tmp_path / "anywhere" / "x.md")).returncode == 2
        # inside t1's scope -> still allowed
        assert _run_hook(tmp_path, file_path=str(tmp_path / "scripts" / "a.py")).returncode == 0

    def test_no_declared_scope_anywhere_grants_legacy_freedom(self, tmp_path):
        # When NOBODY declares a scope, the conservative legacy freedom holds —
        # AC3 only removes the mixed declared+undeclared escape, not adoption.
        _make_db(tmp_path, [("t1", "active", None), ("t2", "active", None)])
        r = _run_hook(tmp_path, file_path=str(tmp_path / "anywhere" / "x.md"))
        assert r.returncode == 0

    def test_notebookedit_gated_on_notebook_path(self, tmp_path):
        # l26-hook-contract-review: NotebookEdit was ungated; it now enforces
        # scope, reading its target from notebook_path (not file_path).
        _make_db(tmp_path, [("t1", "active", '["notebooks/"]')])
        env = os.environ.copy()
        env["TAUSIK_SKIP_HOOKS"] = ""
        env["TAUSIK_HOOK_FAIL_SECURE"] = ""
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        payload = {
            "tool_name": "NotebookEdit",
            "tool_input": {"notebook_path": str(tmp_path / "docs" / "x.ipynb")},
        }
        r = subprocess.run(
            [sys.executable, HOOK],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=10,
        )
        assert r.returncode == 2, r.stderr

    def test_no_active_task_allowed(self, tmp_path):
        _make_db(tmp_path, [("t1", "done", '["scripts/"]')])
        r = _run_hook(tmp_path, file_path=str(tmp_path / "docs" / "x.md"))
        assert r.returncode == 0

    def test_outside_project_root_allowed(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        outside = tmp_path.parent / "elsewhere.md"
        r = _run_hook(tmp_path, file_path=str(outside))
        assert r.returncode == 0

    def test_non_write_tool_ignored(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", "[]")])
        r = _run_hook(tmp_path, tool="Read", file_path=str(tmp_path / "x.md"))
        assert r.returncode == 0

    def test_pre_v30_schema_fails_open(self, tmp_path):
        tausik = tmp_path / ".tausik"
        tausik.mkdir()
        conn = sqlite3.connect(str(tausik / "tausik.db"))
        # ddl-parity: historical — схема ДО v30, без scope_paths: сам предмет
        # теста в том, как хук ведёт себя на такой БД.
        conn.execute("CREATE TABLE tasks (slug TEXT, status TEXT)")
        conn.execute("INSERT INTO tasks VALUES ('t1', 'active')")
        conn.commit()
        conn.close()
        r = _run_hook(tmp_path, file_path=str(tmp_path / "x.md"))
        assert r.returncode == 0

    def test_pre_v30_schema_fail_secure_blocks(self, tmp_path):
        tausik = tmp_path / ".tausik"
        tausik.mkdir()
        conn = sqlite3.connect(str(tausik / "tausik.db"))
        # ddl-parity: historical — та же схема ДО v30, здесь для проверки
        # эскалации TAUSIK_HOOK_FAIL_SECURE на нечитаемой области.
        conn.execute("CREATE TABLE tasks (slug TEXT, status TEXT)")
        conn.execute("INSERT INTO tasks VALUES ('t1', 'active')")
        conn.commit()
        conn.close()
        r = _run_hook(
            tmp_path,
            file_path=str(tmp_path / "x.md"),
            env_extra={"TAUSIK_HOOK_FAIL_SECURE": "1"},
        )
        assert r.returncode == 2

    def test_skip_env_bypasses(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", "[]")])
        r = _run_hook(
            tmp_path,
            file_path=str(tmp_path / "x.md"),
            env_extra={"TAUSIK_SKIP_HOOKS": "1"},
        )
        assert r.returncode == 0

    def test_corrupt_acl_json_treated_as_empty_blocks(self, tmp_path):
        # Lenient reader: corrupt JSON -> empty ACL for that task -> block
        # (the task DECLARED an ACL; we must not fail open on garbage).
        _make_db(tmp_path, [("t1", "active", "{broken")])
        r = _run_hook(tmp_path, file_path=str(tmp_path / "scripts" / "a.py"))
        assert r.returncode == 2

    def test_no_tausik_dir_allowed(self, tmp_path):
        r = _run_hook(tmp_path, file_path=str(tmp_path / "x.md"))
        assert r.returncode == 0
