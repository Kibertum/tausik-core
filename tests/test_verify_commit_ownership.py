"""Regression coverage for commits made by a task other than the one verifying."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import verify_scope_honesty as honesty  # noqa: E402


def _git(root, *args, date=None):
    env = os.environ.copy()
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def _task(slug, status, files, scope_paths=None):
    listed = "\n".join(f'  - "{path}"' for path in files)
    scope_listed = "\n".join(f'  - "{path}"' for path in (scope_paths or []))
    return (
        f"---\nslug: {slug}\nstatus: {status}\nrelevant_files:\n{listed}"
        f"\nscope_paths:\n{scope_listed}\n---\n"
    )


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


def _instructions(dynamic, *, static="static\n"):
    return (
        static
        + "<!-- DYNAMIC:START -->\n"
        + dynamic
        + "\n<!-- DYNAMIC:END -->\n"
    )


@pytest.mark.parametrize("sibling_status", ["active", "blocked", "done"])
def test_committed_sibling_scope_is_not_charged_to_active_task(tmp_path, sibling_status):
    root = _repo(tmp_path)
    _write(root, "foreign.py", "owned by sibling\n")
    _write(root, "tausik/tasks/sibling.md", _task("sibling", sibling_status, ["foreign.py"]))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "commit sibling scope")

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


def test_predeclared_active_sibling_scope_owns_later_commit(tmp_path):
    root = _repo(tmp_path)
    _write(root, "tausik/tasks/sibling.md", _task("sibling", "active", ["foreign.py"]))
    _git(root, "add", "tausik/tasks/sibling.md")
    _git(root, "commit", "-m", "declare sibling scope")
    _write(root, "foreign.py", "owned by predeclared sibling\n")
    _git(root, "add", "foreign.py")
    _git(root, "commit", "-m", "commit sibling implementation")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["status"] == honesty.STATUS_COMPLETE
    assert "foreign.py" not in description["undeclared"]


def test_same_commit_scope_path_glob_owns_matching_state_file(tmp_path):
    root = _repo(tmp_path)
    _write(root, "tausik/tasks/moved.md", "state moved\n")
    _write(
        root,
        "tausik/tasks/sibling.md",
        _task("sibling", "active", [], ["tausik/tasks/*.md"]),
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "move sibling state")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["status"] == honesty.STATUS_COMPLETE


@pytest.mark.parametrize(
    ("status", "changed_path", "content", "expected"),
    [
        ("active", "foreign.py", "outside declared state tree\n", "foreign.py"),
        (
            "planning",
            "tausik/tasks/moved.md",
            "state moved without an active owner\n",
            "tausik/tasks/moved.md",
        ),
    ],
)
def test_same_commit_scope_path_without_active_matching_owner_stays_undeclared(
    tmp_path, status, changed_path, content, expected
):
    root = _repo(tmp_path)
    _write(root, changed_path, content)
    _write(
        root,
        "tausik/tasks/sibling.md",
        _task("sibling", status, [], ["tausik/tasks/*.md"]),
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "commit non-owning scope path")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["undeclared"] == [expected]


def test_ambiguous_predeclared_sibling_scopes_remain_undeclared(tmp_path):
    root = _repo(tmp_path)
    _write(root, "tausik/tasks/sibling.md", _task("sibling", "active", ["foreign.py"]))
    _write(root, "tausik/tasks/other.md", _task("other", "blocked", ["foreign.py"]))
    _git(root, "add", "tausik/tasks")
    _git(root, "commit", "-m", "declare ambiguous sibling scopes")
    _write(root, "foreign.py", "claimed by two predeclared tasks\n")
    _git(root, "add", "foreign.py")
    _git(root, "commit", "-m", "commit ambiguous implementation")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["undeclared"] == ["foreign.py"]


def test_predeclared_planning_scope_does_not_own_later_commit(tmp_path):
    root = _repo(tmp_path)
    _write(root, "tausik/tasks/sibling.md", _task("sibling", "planning", ["foreign.py"]))
    _git(root, "add", "tausik/tasks/sibling.md")
    _git(root, "commit", "-m", "draft sibling scope")
    _write(root, "foreign.py", "not yet active\n")
    _git(root, "add", "foreign.py")
    _git(root, "commit", "-m", "commit unstarted implementation")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["undeclared"] == ["foreign.py"]


def test_missing_predeclared_scope_does_not_own_later_commit(tmp_path):
    root = _repo(tmp_path)
    _write(root, "foreign.py", "no sibling declaration\n")
    _git(root, "add", "foreign.py")
    _git(root, "commit", "-m", "commit undeclared implementation")

    description = honesty.describe_declared_scope(
        ["subject.py", "tausik/tasks/sibling.md"],
        "1970-01-01T00:00:00Z",
        root=str(root),
        task_slug="subject",
    )

    assert description["undeclared"] == ["foreign.py"]


@pytest.mark.parametrize(
    ("sibling_scope", "other_files", "other_scope"),
    [
        (None, ["foreign.py"], None),
        (["*.py"], ["foreign.py"], None),
        (["*.py"], [], ["foreign.*"]),
    ],
    ids=["two-relevant-files", "relevant-files-versus-acl-glob", "two-acl-globs"],
)
def test_two_sibling_exports_in_one_commit_remain_ambiguous(
    tmp_path, sibling_scope, other_files, other_scope
):
    root = _repo(tmp_path)
    _write(root, "foreign.py", "claimed twice\n")
    _write(
        root,
        "tausik/tasks/sibling.md",
        _task("sibling", "active", [] if sibling_scope else ["foreign.py"], sibling_scope),
    )
    _write(root, "tausik/tasks/other.md", _task("other", "active", other_files, other_scope))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "ambiguous sibling scope")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["undeclared"] == ["foreign.py"]


@pytest.mark.parametrize(
    ("moved_status", "moved_scope"),
    [("planning", None), ("active", ["tausik/tasks/moved.md"])],
    ids=["projection-only", "own-export-listed-in-acl"],
)
def test_moved_export_belongs_to_the_acl_owner_not_to_itself(
    tmp_path, moved_status, moved_scope
):
    root = _repo(tmp_path)
    _write(root, "tausik/tasks/moved.md", _task("moved", moved_status, [], moved_scope))
    _write(
        root,
        "tausik/tasks/sibling.md",
        _task("sibling", "active", [], ["tausik/tasks/*.md"]),
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "move a sibling export under an ACL owner")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["status"] == honesty.STATUS_COMPLETE


def test_same_commit_export_outranks_a_predeclared_parent_tree_claim(tmp_path):
    root = _repo(tmp_path)
    _write(root, "tausik/tasks/other.md", _task("other", "active", ["foreign.py"]))
    _git(root, "add", "tausik/tasks/other.md")
    _git(root, "commit", "-m", "predeclare a competing scope")
    _write(root, "foreign.py", "committed with the sibling export\n")
    _write(root, "tausik/tasks/sibling.md", _task("sibling", "active", ["foreign.py"]))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "commit sibling work with its export")

    description = honesty.describe_declared_scope(
        ["subject.py"], "1970-01-01T00:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["status"] == honesty.STATUS_COMPLETE
    assert "foreign.py" not in description["undeclared"]


def _counting_runner(root):
    """The real git, with every invocation's subcommand recorded."""
    import verify_commit_ownership as ownership

    seen = []

    def run(args, **kwargs):
        seen.append(args[1])
        return subprocess.run(args, **kwargs)

    return ownership, seen, run


def test_a_commit_touching_no_inspected_path_costs_no_git_show(tmp_path):
    root = _repo(tmp_path)
    _write(root, "elsewhere.py", "unrelated commit\n")
    _write(root, "tausik/tasks/sibling.md", _task("sibling", "active", ["elsewhere.py"]))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "commit that touches nothing under inspection")
    ownership, seen, run = _counting_runner(root)

    owned = ownership.foreign_completed_paths_since(
        "1970-01-01T00:00:00Z",
        "subject",
        changed_paths={"never-committed.py"},
        root=str(root),
        runner=run,
    )

    assert owned == set()
    assert seen == ["log"], seen


def test_a_commit_touching_an_inspected_path_still_reads_its_exports(tmp_path):
    root = _repo(tmp_path)
    _write(root, "foreign.py", "owned by sibling\n")
    _write(root, "tausik/tasks/sibling.md", _task("sibling", "active", ["foreign.py"]))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "commit sibling scope")
    ownership, seen, run = _counting_runner(root)

    owned = ownership.foreign_completed_paths_since(
        "1970-01-01T00:00:00Z",
        "subject",
        changed_paths={"foreign.py"},
        root=str(root),
        runner=run,
    )

    assert owned == {"foreign.py"}
    assert seen[0] == "log" and "show" in seen and "diff-tree" not in seen, seen


@pytest.mark.parametrize(
    "history",
    ["", "\x01not-a-hash\nfoo.py\n", "foo.py\n\x01\n"],
    ids=["empty", "malformed-header", "orphan-paths"],
)
def test_malformed_history_yields_no_commits(history):
    import verify_commit_ownership as ownership

    assert ownership._commits_with_paths(history) == []


@pytest.mark.parametrize("path", ["AGENTS.md", "CLAUDE.md"])
def test_committed_dynamic_block_only_is_not_charged_to_subject(tmp_path, path):
    root = _repo(tmp_path)
    _write(root, path, _instructions("old"))
    _git(root, "add", path)
    _git(root, "commit", "-m", "add instructions", date="2000-01-01T00:00:00Z")
    _write(root, path, _instructions("new"))
    _git(root, "add", path)
    _git(root, "commit", "-m", "refresh dynamic state", date="2000-01-02T00:00:00Z")

    description = honesty.describe_declared_scope(
        ["subject.py"], "2000-01-01T12:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["status"] == honesty.STATUS_COMPLETE


def test_static_instruction_edit_stays_undeclared(tmp_path):
    root = _repo(tmp_path)
    _write(root, "AGENTS.md", _instructions("old"))
    _git(root, "add", "AGENTS.md")
    _git(root, "commit", "-m", "add instructions", date="2000-01-01T00:00:00Z")
    _write(root, "AGENTS.md", _instructions("new", static="changed static\n"))
    _git(root, "add", "AGENTS.md")
    _git(root, "commit", "-m", "edit instructions", date="2000-01-02T00:00:00Z")

    description = honesty.describe_declared_scope(
        ["subject.py"], "2000-01-01T12:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["undeclared"] == ["AGENTS.md"]


def test_malformed_dynamic_marker_stays_undeclared(tmp_path):
    root = _repo(tmp_path)
    _write(root, "AGENTS.md", _instructions("old"))
    _git(root, "add", "AGENTS.md")
    _git(root, "commit", "-m", "add instructions", date="2000-01-01T00:00:00Z")
    _write(root, "AGENTS.md", "static\n<!-- DYNAMIC:START -->\nnew\n")
    _git(root, "add", "AGENTS.md")
    _git(root, "commit", "-m", "break marker", date="2000-01-02T00:00:00Z")

    description = honesty.describe_declared_scope(
        ["subject.py"], "2000-01-01T12:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["undeclared"] == ["AGENTS.md"]


def test_uncommitted_dynamic_block_stays_undeclared(tmp_path):
    root = _repo(tmp_path)
    _write(root, "AGENTS.md", _instructions("old"))
    _git(root, "add", "AGENTS.md")
    _git(root, "commit", "-m", "add instructions", date="2000-01-01T00:00:00Z")
    _write(root, "AGENTS.md", _instructions("new"))
    _git(root, "add", "AGENTS.md")

    description = honesty.describe_declared_scope(
        ["subject.py"], "2000-01-01T12:00:00Z", root=str(root), task_slug="subject"
    )

    assert description["undeclared"] == ["AGENTS.md"]
