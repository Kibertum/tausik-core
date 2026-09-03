"""A gate is verified by MUTATION, not by passing.

`verify-a-gate-by-mutation-not-by-passing`. A green gate proves only that the
gate did not object; it does not prove the gate would object to anything. The
standard's own senar-14 branch set the example — "six deliberate divergences
introduced one at a time, each caught" — and this repository has paid for the
lesson more than once: sessions #205 and #206 each shipped a regression in a
BLOCKING gate whose tests were green, because the tests asked the gate about
inputs it was already known to handle.

This module turns that discipline into a rule with a closed list. Every gate in
`gate_registry.GATE_REGISTRY` is in exactly one of two tables:

* COVERED — driven here, through the registry's own `impl_for`, on BOTH ends:
  a real violation built under `tmp_path` must come back FAILED, and a clean
  input built the same way must come back PASSED. One end alone proves nothing
  (a gate that is red on every input passes a red-only check as well as a
  correct one). Everything is built under `tmp_path`, so a mutation cannot be
  left behind in the tree — a check that dirtied the repository would be the
  first thing an angry session switches off.
* EXCUSED — not drivable from a synthetic tree in this process (a service-bound
  gate that needs a seeded database and a signed receipt; a command gate whose
  verdict is an external tool's; a warn-severity gate that cannot refuse), with
  the REASON and the names of a red and a green test in the module that does
  drive it. Those names are checked against that module's AST, so a rename or a
  deletion there reddens this table rather than leaving a dangling excuse.

The list is closed: a gate added to the registry without a row here fails
`test_every_registered_gate_is_classified`. Two universes are declared out of
scope on purpose, not forgotten: the PreToolUse hook gates (task_gate,
scope_write_gate, bash_write_gate, memory_pretool_block), which are not
registry gates and are driven through the real hook in their own modules; and
stack-declared command gates (`pytest`, `hadolint` from stacks/*.json), which
are instances of the command runner excused below.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from collections.abc import Callable
from typing import Any

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS_DIR)

from gate_registry import GATE_REGISTRY, impl_for  # noqa: E402

# A builder receives (tmp_path, monkeypatch) and returns whatever the gate's
# registry implementation returned — every implementation unpacks as
# (passed, message), which is all this module reads.
Builder = Callable[[Any, Any], Any]


def _run(name: str, gate_cfg: dict, files: list[str]) -> tuple[bool, str]:
    impl = impl_for(name)
    assert impl is not None, f"{name}: the registry has no implementation to drive"
    passed, message = impl(gate_cfg, files)
    return bool(passed), str(message)


def _write(root, rel: str, body: str) -> str:
    path = root.joinpath(*rel.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return str(path)


# --- filesize -------------------------------------------------------------


def _filesize_red(tmp_path, _mp):
    big = _write(tmp_path, "src/big.py", "x = 1\n" * 600)
    return _run("filesize", {"max_lines": 500}, [big])


def _filesize_green(tmp_path, _mp):
    small = _write(tmp_path, "src/small.py", "x = 1\n" * 10)
    return _run("filesize", {"max_lines": 500}, [small])


# --- class_surface --------------------------------------------------------


def _class_with(n_methods: int) -> str:
    body = "".join(f"    def m{i}(self):\n        pass\n" for i in range(n_methods))
    return f"class Wide:\n{body}"


def _class_surface_at(tmp_path, mp, n_methods: int):
    import gate_class_surface as G

    _write(tmp_path, "scripts/wide.py", _class_with(n_methods))
    _write(tmp_path, ".git/HEAD", "ref: refs/heads/main\n")  # anchors _repo_root
    mp.setattr(G, "_repo_root", lambda: str(tmp_path))
    return _run("class_surface", {}, [])


def _class_surface_red(tmp_path, mp):
    return _class_surface_at(tmp_path, mp, 61)


def _class_surface_green(tmp_path, mp):
    return _class_surface_at(tmp_path, mp, 3)


# --- memory_route ---------------------------------------------------------


def _git(cwd: str, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, stdin=subprocess.DEVNULL
    )


def _memory_route_project(tmp_path, mp):
    import project_config

    root = tmp_path / "proj"
    root.mkdir()
    _git(str(root), "init", "-q")
    _git(str(root), "config", "user.email", "t@t.t")
    _git(str(root), "config", "user.name", "t")
    (root / ".tausik").mkdir()
    _write(root, ".tausik/config.json", "{}\n")
    _write(root, "README.md", "x\n")
    _git(str(root), "add", "-A")
    _git(str(root), "commit", "-qm", "init")
    mp.setattr(project_config, "find_tausik_dir", lambda: str(root / ".tausik"))
    return root


def _memory_route_red(tmp_path, mp):
    root = _memory_route_project(tmp_path, mp)
    _write(root, ".cursor/rules/learned.mdc", "db host is x\n")  # a foreign memory sink
    return _run("memory_route", {}, [])


def _memory_route_green(tmp_path, mp):
    _memory_route_project(tmp_path, mp)
    return _run("memory_route", {}, [])


# --- bootstrap_drift ------------------------------------------------------


def _bootstrap_project(tmp_path, mp, deployed: str):
    (tmp_path / ".tausik").mkdir()
    mp.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
    _write(tmp_path, "scripts/a.py", "x = 1\n")
    _write(tmp_path, ".claude/scripts/a.py", deployed)
    return _run("bootstrap_drift", {}, [])


def _bootstrap_drift_red(tmp_path, mp):
    return _bootstrap_project(tmp_path, mp, "x = 0\n")  # the edit never reached the copy


def _bootstrap_drift_green(tmp_path, mp):
    return _bootstrap_project(tmp_path, mp, "x = 1\n")


# --- skill_spec_conformance -----------------------------------------------


def _skill(tmp_path, dir_name: str, name: str) -> str:
    return _write(
        tmp_path,
        f"skills/{dir_name}/SKILL.md",
        f"---\nname: {name}\ndescription: A skill.\n---\n\nBody.\n",
    )


def _skill_spec_red(tmp_path, _mp):
    return _run("skill_spec_conformance", {}, [_skill(tmp_path, "good-dir", "Other Name")])


def _skill_spec_green(tmp_path, _mp):
    return _run("skill_spec_conformance", {}, [_skill(tmp_path, "good-dir", "good-dir")])


# --- state_roundtrip ------------------------------------------------------


def _state_project(tmp_path, mp):
    import project_config
    import state_triggers
    from project_backend import SQLiteBackend
    from project_service import ProjectService
    from state_export import ENTITY_DIRS, build_tree
    from state_serialize import write_tree

    mp.setattr(state_triggers, "_auto_export_enabled", lambda _d: False)
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    svc = ProjectService(SQLiteBackend(str(tausik_dir / "tausik.db")))
    svc.epic_add("e1", "Epic One")
    svc.story_add("e1", "s1", "Story One")
    svc.task_add("s1", "t1", "Task One", complexity="simple", role="developer")
    tree, _w = build_tree(svc)
    svc.be.close()
    write_tree(str(tmp_path / "tausik"), tree, managed_dirs=set(ENTITY_DIRS))
    mp.setattr(project_config, "find_tausik_dir", lambda: str(tausik_dir))


def _state_roundtrip_red(tmp_path, mp):
    _state_project(tmp_path, mp)
    exported = sorted(
        os.path.join(d, f)
        for d, _dirs, fs in os.walk(tmp_path / "tausik")
        for f in fs
        if f.endswith(".md")
    )
    assert exported, "the projection wrote nothing to hand-edit"
    with open(exported[0], "a", encoding="utf-8") as fh:
        fh.write("\nhand-edited: yes\n")  # the tree no longer matches the DB
    return _run("state_roundtrip", {}, [])


def _state_roundtrip_green(tmp_path, mp):
    _state_project(tmp_path, mp)
    return _run("state_roundtrip", {}, [])


# --- the two tables ---------------------------------------------------------

COVERED: dict[str, tuple[Builder, Builder]] = {
    "filesize": (_filesize_red, _filesize_green),
    "class_surface": (_class_surface_red, _class_surface_green),
    "memory_route": (_memory_route_red, _memory_route_green),
    "bootstrap_drift": (_bootstrap_drift_red, _bootstrap_drift_green),
    "skill_spec_conformance": (_skill_spec_red, _skill_spec_green),
    "state_roundtrip": (_state_roundtrip_red, _state_roundtrip_green),
}

# gate -> (reason, module, red test, green test). The module is the one that
# DOES drive both ends; the names are verified against its AST below.
EXCUSED: dict[str, tuple[str, str, str, str]] = {
    "ruff": (
        "command gate: the verdict is the external tool's; the runner's red/green "
        "wiring and the anti-neutering guard are driven in their own modules",
        "test_gate_command_runner.py",
        "test_failure_output_states_it_too",
        "test_pass_output_states_how_much_of_the_suite_ran",
    ),
    "mypy": (
        "command gate, severity warn (cannot refuse): same runner as ruff",
        "test_gate_command_runner.py",
        "test_failure_output_states_it_too",
        "test_pass_output_states_how_much_of_the_suite_ran",
    ),
    "bandit": (
        "command gate, severity warn, disabled by default: same runner as ruff",
        "test_gate_command_runner.py",
        "test_failure_output_states_it_too",
        "test_pass_output_states_how_much_of_the_suite_ran",
    ),
    "tdd_order": (
        "severity warn and disabled by default: it cannot refuse a close, so a "
        "mutation cannot be 'caught'; both ends are driven on the pure function",
        "test_gate_tdd_order.py",
        "test_source_without_test_blocks",
        "test_source_with_test_passes",
    ),
    "renar_drift_schema": (
        "severity warn (cannot refuse); needs a seeded RENAR store, driven there",
        "test_renar_drift.py",
        "test_adapt_delta_orphan",
        "test_clean_artifacts_zero_findings",
    ),
    "renar_drift_provenance": (
        "severity warn (cannot refuse); needs a seeded SPEC/task/verify chain",
        "test_renar_drift7_provenance.py",
        "test_a_spec_edited_after_the_verification_is_stale",
        "test_a_task_verified_after_the_spec_edit_is_not_stale",
    ),
    "claudemd_state_drift": (
        "needs a live DB with knowledge AND a rendered CLAUDE.md; its red end is "
        "driven against real corrupted snapshots out of git history, which a "
        "synthetic tree cannot reproduce honestly",
        "test_claudemd_state_gate.py",
        "test_replacing_the_block_with_an_empty_project_reds",
        "test_the_gate_is_green_end_to_end_on_this_repository",
    ),
    "verify_first": (
        "service-bound (`svc:_enforce_verify_first`): needs a seeded DB, a task "
        "in flight and a signed verify receipt; driven through the service",
        "test_verify_first_contract.py",
        "test_no_verify_run_blocks",
        "test_fresh_verify_run_unblocks",
    ),
    "changelog": (
        "service-bound (`svc:_enforce_changelog`): needs a service and a git diff",
        "test_changelog_gate.py",
        "test_one_file_missing_blocks_naming_it",
        "test_both_files_written_allows",
    ),
}


def _test_names_in(module_file: str) -> set[str]:
    with open(os.path.join(TESTS_DIR, module_file), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test")
    }


# --- the rule ---------------------------------------------------------------


def test_every_registered_gate_is_classified():
    """The closed list: a new gate must be either driven here or excused with
    a reason and a reference. Silence is the one thing not allowed."""
    registry = set(GATE_REGISTRY)
    assert set(COVERED) & set(EXCUSED) == set()
    assert set(COVERED) | set(EXCUSED) == registry, {
        "unclassified": sorted(registry - set(COVERED) - set(EXCUSED)),
        "stale rows": sorted((set(COVERED) | set(EXCUSED)) - registry),
    }


@pytest.mark.parametrize("name", sorted(COVERED))
def test_a_real_violation_is_refused(name, tmp_path, monkeypatch):
    red, _green = COVERED[name]
    passed, message = red(tmp_path, monkeypatch)
    assert passed is False, f"{name} let a real violation through: {message}"


@pytest.mark.parametrize("name", sorted(COVERED))
def test_a_clean_input_is_allowed(name, tmp_path, monkeypatch):
    """The other end. Without it a gate that is red on everything passes."""
    _red, green = COVERED[name]
    passed, message = green(tmp_path, monkeypatch)
    assert passed is True, f"{name} refused a clean input: {message}"


@pytest.mark.parametrize("name", sorted(EXCUSED))
def test_an_excuse_names_a_reason_and_both_ends_that_exist(name):
    reason, module_file, red_test, green_test = EXCUSED[name]
    assert len(reason) > 20, f"{name}: an excuse needs a reason, not a label"
    names = _test_names_in(module_file)
    assert red_test in names, f"{name}: red end {red_test!r} is not in {module_file}"
    assert green_test in names, f"{name}: green end {green_test!r} is not in {module_file}"
    assert red_test != green_test


def test_the_table_leaves_the_repository_untouched(tmp_path, monkeypatch):
    """Every builder works under tmp_path — and that is CHECKED, not assumed:
    every file opened for writing while the table runs must lie under this
    test's own tmp_path, or the test names it.

    Why not `git status` before and after? Measured in #207: under xdist a
    builder that dropped a file into `tests/` survived that check, because
    another worker had already run the same builder before this test took
    its "before" snapshot, and the leftover was in both. Intercepting the
    write is independent of ordering.

    THREE CHANNELS are watched, because the builders use three (review #207,
    record #12: the first version watched one and promised all): `open` —
    `io.open` as well as `builtins.open`, since `Path.write_text` goes through
    the former; `sqlite3.connect`, through which `state_roundtrip` creates its
    database; and `subprocess.run`/`Popen`, through which `memory_route` runs
    `git` — for those the working directory and every absolute argument are
    what can be observed, and what the child then writes on its own is not.
    NOT watched, and said so: `os.open` and other direct syscalls.
    """
    import builtins
    import io
    import sqlite3

    written: list[str] = []
    real_open, real_connect = builtins.open, sqlite3.connect
    real_run, real_popen = subprocess.run, subprocess.Popen

    def note(path) -> None:
        if isinstance(path, str | os.PathLike) and os.fspath(path) not in ("", ":memory:"):
            written.append(os.path.abspath(os.fspath(path)))

    def spy_open(file, mode="r", *args, **kwargs):
        if any(c in str(mode) for c in "wax+"):
            note(file)
        return real_open(file, mode, *args, **kwargs)

    def spy_connect(database, *args, **kwargs):
        note(database)
        return real_connect(database, *args, **kwargs)

    def spy_process(real):
        def run(argv, *args, **kwargs):
            note(kwargs.get("cwd") or os.getcwd())
            for a in argv if isinstance(argv, list | tuple) else [argv]:
                if isinstance(a, str | os.PathLike) and os.path.isabs(os.fspath(a)):
                    note(a)
            return real(argv, *args, **kwargs)

        return run

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(io, "open", spy_open)
    monkeypatch.setattr(sqlite3, "connect", spy_connect)
    monkeypatch.setattr(subprocess, "run", spy_process(real_run))
    monkeypatch.setattr(subprocess, "Popen", spy_process(real_popen))
    cwd = os.getcwd()
    for name, (red, green) in sorted(COVERED.items()):
        for end, builder in (("red", red), ("green", green)):
            root = tmp_path / name / end
            root.mkdir(parents=True)
            with monkeypatch.context() as mp:
                builder(root, mp)
    assert os.getcwd() == cwd
    allowed = os.path.abspath(str(tmp_path))
    outside = sorted({p for p in written if not p.startswith(allowed)})
    assert outside == [], f"a builder touched a path outside tmp_path: {outside}"
    assert written, "no write was observed at all — the spies are not seeing the builders"
    # Each channel must have been exercised, or a builder could switch to an
    # unwatched one and this test would keep passing for the wrong reason.
    assert any(p.endswith(".db") for p in written), "the sqlite channel saw nothing"
    assert any(p.endswith(("proj", "proj" + os.sep + ".git")) for p in written), (
        "the subprocess channel saw nothing"
    )


CROSSCUTTING_SCOPE = ["tests/"]
