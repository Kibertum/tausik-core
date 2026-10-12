"""A directory git cannot see is how a shell artefact survives in a tree for months.

WHAT WAS FOUND BY HAND. A repository inventory turned up three directories nobody made on purpose:
one named after an unexpanded shell variable and two named after fragments of a `git config`
command that became redirect targets, aged 24 to 46 days. None appeared in `git status`, because
git tracks FILES: an empty directory has none, so `git status` is silent, `.gitignore` has nothing
to say, and every gate looks straight through it.

THE DETECTOR TOOK THREE DRAFTS AND THE NUMBERS ARE WHY THE FIRST TWO WERE NOT GOOD ENOUGH:

  * 543 findings with a hand-written exception list of two entries — the deployed profile trees are
    gitignored wholesale, so every directory inside them counted. True, and useless.
  * 197 after reading the project's registries of generated trees — still leaking, because there
    are FOUR registries of deployed layouts and `.agents` was in neither of the two consulted.
  * 5 once the question was put to GIT: is the DIRECTORY ITSELF ignored? That needs no registry at
    all. Every machine-written tree here is ignored as a directory; the three artefacts are not.

A detector that reports 543 or 197 items teaches the reader to skim it, which is the same death
the artefacts already survived once.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from invisible_dirs import DECLARED_EMPTY, find, render  # noqa: E402


@pytest.fixture
def tree(tmp_path):
    """A tree holding one of each: residue, plain empty, ignored, and a normal directory."""
    (tmp_path / "$SCRATCH").mkdir()
    (tmp_path / "lf").mkdir()
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "code.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "nested" / "deep").mkdir(parents=True)
    (tmp_path / "nested" / "deep" / "file.txt").write_text("y\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "empty_inside").mkdir()
    return tmp_path


def _ignores_claude(rel: str) -> bool:
    return rel == ".claude" or rel.startswith(".claude/")


def test_the_artefacts_are_found_and_named_by_kind(tree):
    found = {f.path: f.kind for f in find(str(tree), _ignores_claude)}
    assert found.get("$SCRATCH") == "shell-residue", "a name a shell would have eaten"
    assert found.get("lf") == "empty", "plainly empty, no metacharacter"


def test_a_directory_with_a_file_at_any_depth_is_not_a_finding(tree):
    paths = {f.path for f in find(str(tree), _ignores_claude)}
    assert "real" not in paths
    assert "nested" not in paths, "a file two levels down still makes the parent visible"


def test_an_ignored_directory_is_machine_territory_and_is_not_descended(tree):
    """THE NEGATIVE THE FIRST TWO DRAFTS FAILED: 543 findings came from walking into these.

    Every deployed profile and generated tree in this project is ignored as a directory, so git's
    own answer separates machine territory from a mistake without any list to maintain.
    """
    paths = {f.path for f in find(str(tree), _ignores_claude)}
    assert ".claude" not in paths
    assert ".claude/empty_inside" not in paths, "the whole subtree is skipped, not just the root"


def test_without_the_git_probe_nothing_is_assumed_ignored(tree):
    """Omitting the probe must not silently empty the report — it widens it, visibly.

    A broken git that made everything look ignored would turn this check off without saying so,
    which is the failure mode the project rules out by decision #157.
    """
    paths = {f.path for f in find(str(tree))}
    assert ".claude" in paths, "with no probe, an ignored tree is just another empty directory"


def test_every_declared_exception_states_its_reason():
    """The list is EMPTY today, and that is the finding rather than an omission.

    Two entries lived in it — the agent worktree root and a vendored repository — and both became
    redundant the moment the check asked git whether the directory ITSELF is ignored: git ignores
    both. A hand-written list duplicating git's answer is a second source of truth, and that one
    also hardcoded ONE profile directory while the engine supports seven. The mechanism stays for a
    deliberate empty directory that git DOES see, and then the reason is required.
    """
    for path, reason in DECLARED_EMPTY.items():
        assert len(reason) > 30, f"{path}: {reason!r} is not a reason"


def test_the_report_says_what_to_do_with_each_kind(tree):
    text = render(find(str(tree), _ignores_claude))
    assert "DECLARED_EMPTY" in text, "it names the way to declare one, not just the finding"
    assert "outlives the mistake" in text


def test_nothing_found_prints_nothing(tmp_path):
    (tmp_path / "full").mkdir()
    (tmp_path / "full" / "f.txt").write_text("x", encoding="utf-8")
    assert render(find(str(tmp_path))) == ""


def test_the_live_tree_is_within_its_ratchet():
    """The threshold is taken AFTER the cleanup, not before — a ratchet on the old numbers would
    have frozen three artefacts in place as though they were declared."""
    import functools
    import json
    import subprocess

    ratchet = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
    limit = ratchet["repo_hygiene"]["invisible_dirs"]["findings"]

    @functools.lru_cache(maxsize=None)
    def is_ignored(rel: str) -> bool:
        done = subprocess.run(  # ruff-not-enabled: S603 - fixed argv, shell=False
            ["git", "check-ignore", "-q", "--", rel],
            cwd=_REPO,
            capture_output=True,
            timeout=10,
            check=False,
        )
        return done.returncode == 0

    found = find(str(_REPO), is_ignored)
    assert len(found) <= limit, [f"{f.path} [{f.kind}]" for f in found]
