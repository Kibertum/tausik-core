"""Regression coverage for commits made by a task other than the one verifying."""

from __future__ import annotations

import os
import subprocess
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import verify_scope_honesty as honesty  # noqa: E402


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _task(slug, status, files):
    listed = "\n".join(f'  - "{path}"' for path in files)
    return f"---\nslug: {slug}\nstatus: {status}\nrelevant_files:\n{listed}\n---\n"


def _write(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")


def _repo(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _write(tmp_path, "tausik/tasks/sibling.md", _task("sibling", "planning", []))
    _write(tmp_path, "subject.py", "before\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "seed")
    return tmp_path


def test_completed_sibling_commit_is_not_charged_to_active_task(tmp_path):
    root = _repo(tmp_path)
    _write(root, "foreign.py", "owned by sibling\n")
    _write(root, "tausik/tasks/sibling.md", _task("sibling", "done", ["foreign.py"]))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "complete sibling")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["status"] == honesty.STATUS_COMPLETE
    assert "foreign.py" not in description["undeclared"]


def test_uncommitted_undeclared_path_still_reddens_after_sibling_commit(tmp_path):
    root = _repo(tmp_path)
    _write(root, "foreign.py", "owned by sibling\n")
    _write(root, "tausik/tasks/sibling.md", _task("sibling", "done", ["foreign.py"]))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "complete sibling")
    _write(root, "secret.py", "still active task work\n")
    _git(root, "add", "secret.py")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["status"] == honesty.STATUS_UNDER_DECLARED
    assert description["undeclared"] == ["secret.py"]
