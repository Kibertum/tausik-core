"""`ruff format` has a verdict that blocks, and the inherited debt only shrinks
(ruff-format-is-not-gated-and-86-files-diverged, decision #386)."""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import gate_ruff_format as g  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "harness/", "bootstrap/", "tests/"]


@pytest.fixture
def scratch_file(tmp_path, monkeypatch):
    """A task file inside a throwaway repository root, never the real tree."""
    monkeypatch.setattr(g, "_repo_root", lambda: str(tmp_path))
    (tmp_path / "scripts").mkdir()
    return str(tmp_path / "scripts" / "probe.py")


def test_an_unformatted_task_file_blocks(scratch_file):
    with open(scratch_file, "w", encoding="utf-8") as f:
        f.write("x = {  'a':1 }\n")
    ok, msg = g.run_ruff_format_gate({}, [scratch_file])
    assert not ok and "probe.py" in msg and "ruff format" in msg


def test_a_formatted_task_file_passes(scratch_file):
    with open(scratch_file, "w", encoding="utf-8") as f:
        f.write('x = {"a": 1}\n')
    ok, _ = g.run_ruff_format_gate({}, [scratch_file])
    assert ok


def test_a_file_on_the_legacy_list_is_not_checked():
    legacy = sorted(g.legacy_unformatted() or [])
    assert legacy, "the frozen list is adopted"
    ok, msg = g.run_ruff_format_gate({}, [os.path.join(_ROOT, legacy[0])])
    assert ok and "no task file to check" in msg


def _tree_unformatted() -> set[str]:
    """The tree's divergence, through the gate's own ruff and parser."""
    found = g.unformatted(["scripts", "harness", "bootstrap", "tests"], _ROOT)
    assert found is not None, "ruff could not run"
    return set(found)


def test_the_legacy_list_only_shrinks():
    legacy = g.legacy_unformatted() or set()
    now = _tree_unformatted()
    formatted_since = sorted(legacy - now)
    new_divergence = sorted(now - legacy)
    assert not formatted_since, (
        f"formatted since the list was frozen — remove from tausik/gates.json: {formatted_since}"
    )
    assert not new_divergence, f"not on the frozen list — format them: {new_divergence}"


def test_the_deployed_copy_finds_the_project_root_not_claude_dir(tmp_path):
    """Gates run from `.claude/scripts/`; dirname-twice would land on `.claude/`.

    Measured in session #269: the deployed gate read no frozen list and named a
    listed legacy file `../scripts/gate_test_resolver.py` — refused as new debt.
    """
    (tmp_path / ".git").mkdir()
    deployed = tmp_path / ".claude" / "scripts"
    deployed.mkdir(parents=True)
    assert g._repo_root(str(deployed)) == str(tmp_path)


def test_without_a_git_anchor_the_old_reading_stays(tmp_path):
    here = tmp_path / "scripts"
    here.mkdir()
    assert g._repo_root(str(here)) == str(tmp_path)
