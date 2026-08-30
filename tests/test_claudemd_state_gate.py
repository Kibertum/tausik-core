"""The CLAUDE.md dynamic block must be a rendering of THIS database.

claudemd-drift-gates-do-not-notice-an-emptied-dynamic-block. The block was
overwritten with the shape of an empty project ("Tasks: 0/1 done", memory tail
gone) and that wipe reached TWENTY commits between the v1.0.0 release and
2026-08-26, surviving full green suites, signed verify receipts and QG-2 closes.
These tests are the guard that was missing, and they are anchored to real bytes:
the repository's own CLAUDE.md as it stands, and three corrupted snapshots pulled
out of git history — not to invented fixtures that only prove the code equals
itself (convention #266).

WHY THE MUTATION IS NOT PERFORMED ON THE FILE IN THE TREE. The lane runs
``-n auto``: mutating the repository's CLAUDE.md in place would be visible to
every other worker, and tests/test_claude_md_size.py reads that exact file. So
the mutation here is applied to the real file's real BYTES in memory, which
proves the same thing about the same content. The on-disk end-to-end mutation
(wipe, run the gate, restore from a byte copy, compare sha256 before/after) was
performed once by hand as the task's AC-3 evidence and is recorded in its journal.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from gate_claudemd_state import (  # noqa: E402
    block_carries_memory_tail,
    extract_dynamic_block,
    run_claudemd_state_gate,
)

# The tail's first line. It is NOT a constant this test believes on its own —
# test_the_sentinel_is_the_producers_own_first_line pins it to the producer, so a
# rename there reds here instead of silently blinding every assertion below.
SENTINEL = "### Memory tail"

# The wipe, verbatim, as it was found in the tree on 2026-08-30 and in twenty
# commits before it: a freshly initialised project's state written to this
# repository's path.
EMPTY_PROJECT_BLOCK = (
    "\n## Current State\n"
    "Session: none | Branch: v1-9-wave | Version: 1.8.0\n"
    "Tasks: 0/1 done, 0 active, 0 blocked\n"
)

# Three of the twenty corrupted snapshots, deliberately spread across the whole
# life of the project: the first release, the 1.4 release, and the most recent
# one. If the gate reds on all three it would have caught the defect for four
# months, not merely in the shape it wore today.
CORRUPTED_SNAPSHOTS = [
    ("a158380", "Initial release: TAUSIK v1.0.0, 2026-04-10"),
    ("b5ec2c6", "release(v1.4.0), 2026-05-03"),
    ("82b8ed7", "feat(1.9): tausik audit evidence, 2026-08-26"),
]


def _git_show(sha: str, path: str) -> str | None:
    """`git show <sha>:<path>`, or None when unavailable (shallow clone, no git)."""
    try:
        proc = subprocess.run(
            ["git", "show", f"{sha}:{path}"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception:  # noqa: BLE001 — no git binary / timeout: the check is skipped, not failed
        return None
    return proc.stdout if proc.returncode == 0 else None


def _real_block(name: str) -> str:
    text = (REPO_ROOT / name).read_text(encoding="utf-8")
    block = extract_dynamic_block(text)
    assert block is not None, f"{name} lost its DYNAMIC markers"
    return block


class TestTheFormatIsAskedNotAssumed:
    """The gate reads the producer's output; so must the tests."""

    def test_the_sentinel_is_the_producers_own_first_line(self):
        """SENAR: pin the literal to its source, or the guard rots on a rename."""
        import service_knowledge_aggregates as ska

        class _Be:
            def decision_list(self, n):
                return []

            def memory_list(self, kind, n):
                return [{"id": 1, "title": "x"}] if kind == "convention" else []

        tail = ska.build_compact_memory_tail(_Be())
        assert tail, "a DB with one convention must still produce a tail"
        assert tail[0] == SENTINEL, (
            f"the producer's first tail line is {tail[0]!r}, the gate's tests assume "
            f"{SENTINEL!r} — they have drifted apart"
        )


class TestTheRealTreeIsIntact:
    """The repository's own files, as they stand right now."""

    @pytest.mark.parametrize("name", ["CLAUDE.md", "AGENTS.md"])
    def test_the_dynamic_block_carries_a_memory_tail(self, name):
        assert block_carries_memory_tail(_real_block(name), SENTINEL), (
            f"{name} carries a DYNAMIC block with no memory tail — it was not "
            "rendered from this project's database. Fix: tausik update-claudemd"
        )

    def test_the_gate_is_green_end_to_end_on_this_repository(self):
        if not (REPO_ROOT / ".tausik" / "tausik.db").is_file():
            pytest.skip("no .tausik/tausik.db in this checkout")
        passed, message = run_claudemd_state_gate()
        assert passed, message


class TestTheWipeIsCaught:
    """The negative scenario, on real bytes."""

    @pytest.mark.parametrize("name", ["CLAUDE.md", "AGENTS.md"])
    def test_replacing_the_block_with_an_empty_project_reds(self, name):
        """Both sides of the same file: intact passes, wiped fails."""
        intact = _real_block(name)
        assert block_carries_memory_tail(intact, SENTINEL)
        assert not block_carries_memory_tail(EMPTY_PROJECT_BLOCK, SENTINEL), (
            "the empty-project block was accepted — this gate would have watched "
            "the wipe reach twenty commits exactly as the old ones did"
        )

    def test_a_tail_header_with_nothing_under_it_is_not_a_tail(self):
        """An emptied section carries as little context as a missing one."""
        assert not block_carries_memory_tail(f"\n## Current State\n{SENTINEL}\n", SENTINEL)

    @pytest.mark.parametrize("sha,what", CORRUPTED_SNAPSHOTS)
    def test_historical_corrupted_snapshots_are_all_red(self, sha, what):
        """Four months of history, not today's shape only."""
        text = _git_show(sha, "CLAUDE.md")
        if text is None:
            pytest.skip(f"{sha} unavailable in this checkout")
        block = extract_dynamic_block(text)
        assert block is not None, f"{sha} has no DYNAMIC block at all"
        assert "Tasks: 0/1 done" in block, (
            f"{sha} ({what}) was recorded as carrying the wipe and does not — "
            "the evidence behind this gate is stale"
        )
        assert not block_carries_memory_tail(block, SENTINEL), (
            f"the gate would have passed {sha} ({what}), one of the twenty commits "
            "that carried the corruption into the repository"
        )


class TestStalenessIsNotDrift:
    """The gate must survive the state every session is in between refreshes."""

    def test_an_out_of_date_but_intact_block_is_green(self):
        """Counters lag the DB after every close; that is normal, not corruption."""
        stale = re.sub(
            r"^Tasks: .*$",
            "Tasks: 973/1038 done, 0 active, 0 blocked",
            _real_block("CLAUDE.md"),
            count=1,
            flags=re.M,
        )
        assert "973/1038" in stale, "the substitution did not apply — test is vacuous"
        assert block_carries_memory_tail(stale, SENTINEL), (
            "a block with stale counters but a live memory tail was called drift; "
            "a gate that reds on ordinary staleness gets switched off in a day"
        )

    def test_an_intact_block_from_git_history_is_green(self):
        """A real past rendering of this project, not a hand-made one."""
        text = _git_show("HEAD~1", "CLAUDE.md")
        if text is None:
            pytest.skip("HEAD~1 unavailable in this checkout")
        block = extract_dynamic_block(text)
        assert block is not None
        if "Tasks: 0/1 done" in block:
            pytest.skip("HEAD~1 itself carries the wipe")
        assert block_carries_memory_tail(block, SENTINEL)


class TestItIsSilentWhereItCannotJudge:
    """Four skip paths — a guard with no basis must not invent a verdict."""

    def test_a_file_without_markers_yields_no_block(self):
        assert extract_dynamic_block("# Just a document\n\nNo markers here.\n") is None

    def test_no_database_skips(self, monkeypatch, tmp_path):
        import project_config

        empty = tmp_path / ".tausik"
        empty.mkdir()
        monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(empty))
        passed, message = run_claudemd_state_gate()
        assert passed
        assert "tausik.db" in message

    def test_no_claudemd_skips(self, monkeypatch):
        if not (REPO_ROOT / ".tausik" / "tausik.db").is_file():
            pytest.skip("no .tausik/tausik.db in this checkout")
        import claudemd_state

        monkeypatch.setattr(claudemd_state, "resolve_claudemd", lambda project_dir: None)
        passed, message = run_claudemd_state_gate()
        assert passed
        assert "No CLAUDE.md" in message

    def test_an_empty_knowledge_base_owes_no_tail(self, monkeypatch):
        if not (REPO_ROOT / ".tausik" / "tausik.db").is_file():
            pytest.skip("no .tausik/tausik.db in this checkout")
        import service_knowledge_aggregates as ska

        monkeypatch.setattr(ska, "build_compact_memory_tail", lambda be: [])
        passed, message = run_claudemd_state_gate()
        assert passed
        assert "knowledge base is empty" in message


class TestItNeverCrashesTheCommitItGuards:
    def test_an_internal_fault_fails_open(self, monkeypatch):
        if not (REPO_ROOT / ".tausik" / "tausik.db").is_file():
            pytest.skip("no .tausik/tausik.db in this checkout")
        import claudemd_state

        def _boom(project_dir):
            raise RuntimeError("resolver exploded")

        monkeypatch.setattr(claudemd_state, "resolve_claudemd", _boom)
        passed, message = run_claudemd_state_gate()
        assert passed, "a gate that raises takes the whole commit-gate run down with it"
        assert "unavailable" in message
        assert "resolver exploded" in message


class TestItIsWiredIntoTheRegistry:
    def test_the_registry_carries_the_gate_and_blocks_on_it(self):
        from gate_registry import GATE_REGISTRY

        spec = GATE_REGISTRY.get("claudemd_state_drift")
        assert spec is not None, "the gate exists but nothing runs it"
        assert spec.default_config["severity"] == "block"
        assert spec.default_config["enabled"] is True
        assert set(spec.default_config["trigger"]) == {"task-done", "commit"}

    def test_the_registry_impl_points_at_this_module(self):
        from gate_registry import GATE_REGISTRY

        spec = GATE_REGISTRY["claudemd_state_drift"]
        module, _, func = spec.impl.partition(":")
        assert (module, func) == ("gate_claudemd_state", "run_claudemd_state_gate_for")
        # Resolvable, not merely spelled right: an impl string that imports
        # nothing is a gate that CANNOT-RUN and therefore certifies nothing.
        mod = __import__(module)
        assert callable(getattr(mod, func))
