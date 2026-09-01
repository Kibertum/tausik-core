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

from conftest import DORMANT_WITHOUT_LIVE_DB  # noqa: E402

from gate_claudemd_state import (  # noqa: E402
    block_carries_memory_tail,
    extract_dynamic_block,
    run_claudemd_state_gate,
)

# Bound at import, BEFORE conftest's autouse `_mock_run_gates` replaces the
# module attribute with a stub that answers `(True, [])`. The same escape
# tests/test_gate_registry.py and tests/test_gates.py use: calling
# `gate_runner.run_gates` from inside a test would measure the mock, and a test
# about what a receipt records must run the code that records it.
from backend_schema_gate_runs import GATE_RUNS_SQL  # noqa: E402
from gate_runner import run_gates  # noqa: E402

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
            pytest.skip(DORMANT_WITHOUT_LIVE_DB)
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
            pytest.skip(DORMANT_WITHOUT_LIVE_DB)
        import claudemd_state

        monkeypatch.setattr(claudemd_state, "resolve_claudemd", lambda project_dir: None)
        passed, message = run_claudemd_state_gate()
        assert passed
        assert "No CLAUDE.md" in message

    def test_an_empty_knowledge_base_owes_no_tail(self, monkeypatch):
        if not (REPO_ROOT / ".tausik" / "tausik.db").is_file():
            pytest.skip(DORMANT_WITHOUT_LIVE_DB)
        import service_knowledge_aggregates as ska

        monkeypatch.setattr(ska, "build_compact_memory_tail", lambda be: [])
        passed, message = run_claudemd_state_gate()
        assert passed
        assert "knowledge base is empty" in message


class TestItNeverCrashesTheCommitItGuards:
    """INVERTED, deliberately, and left in place rather than deleted.

    This class used to hold `test_an_internal_fault_fails_open`, asserting
    `passed` on a raised exception. That assertion PINNED the defect
    claudemd-state-gate-reports-passed-when-it-could-not-run: session #192's
    receipt signed this block-severity gate as PASSED while its own text said
    "check unavailable (RuntimeError: Database schema v48 is newer than code
    v47)". The test was green throughout, because it was measuring exactly the
    behaviour that was wrong.

    Two claims were tangled in that one assertion, and only one of them was
    ever true: (1) the gate must not let the exception escape and crash the
    commit — TRUE, kept, tested below; (2) therefore the run counts as a pass —
    FALSE, and the whole cost of the defect. They are now separate tests, so
    the survivor cannot smuggle the other back in.
    """

    def test_an_internal_fault_does_not_escape(self, monkeypatch):
        if not (REPO_ROOT / ".tausik" / "tausik.db").is_file():
            pytest.skip(DORMANT_WITHOUT_LIVE_DB)
        import claudemd_state

        def _boom(project_dir):
            raise RuntimeError("resolver exploded")

        monkeypatch.setattr(claudemd_state, "resolve_claudemd", _boom)
        outcome = run_claudemd_state_gate()  # must not raise
        assert "unavailable" in outcome.message
        assert "resolver exploded" in outcome.message

    def test_an_internal_fault_is_recorded_as_non_execution_not_as_a_pass(self, monkeypatch):
        if not (REPO_ROOT / ".tausik" / "tausik.db").is_file():
            pytest.skip(DORMANT_WITHOUT_LIVE_DB)
        import claudemd_state
        import gate_outcome

        def _boom(project_dir):
            raise RuntimeError("resolver exploded")

        monkeypatch.setattr(claudemd_state, "resolve_claudemd", _boom)
        outcome = run_claudemd_state_gate()
        assert outcome.outcome == gate_outcome.COULD_NOT_RUN
        assert outcome.reason_code == gate_outcome.REASON_RUNNER_ERROR
        assert not outcome.ran, "a check that raised produced no verdict to certify with"
        assert outcome.blocks, (
            "severity=block and no evidence: SENAR 1.4 §8.6(e) — the absence of a "
            "negative finding is not a positive verdict"
        )
        assert outcome.remedy, "a refusal without a next action is the #182 dead end again"

    def test_a_fault_finding_the_project_is_also_non_execution(self, monkeypatch):
        """The gate has TWO fail-open sites, and the second test did not reach the first.

        Found by the AC5 mutation, not by reading: reverting the earlier block —
        the one wrapping `find_tausik_dir` and the database-path probe — to
        `return True, "...unavailable..."` left the whole file green. A site no
        test reaches is a site the fix is not proven at, so it gets its own
        measurement rather than a shared one.
        """
        import gate_outcome
        import project_config

        def _boom(*a, **k):
            raise OSError("cannot locate .tausik")

        monkeypatch.setattr(project_config, "find_tausik_dir", _boom)
        outcome = run_claudemd_state_gate()  # must not raise
        assert outcome.outcome == gate_outcome.COULD_NOT_RUN
        assert outcome.reason_code == gate_outcome.REASON_RUNNER_ERROR
        assert outcome.blocks
        assert "cannot locate .tausik" in outcome.message


class TestNothingToJudgeIsNotTheSameAsCouldNotJudge:
    """AC2: the honest skips must stay non-blocking AND stay distinguishable.

    Collapsing them into COULD_NOT_RUN would trade one indistinguishability for
    another — a fresh clone with no database has nothing to render and is not at
    fault. Collapsing them into ONE reason code would leave the receipt unable to
    say WHICH empty state it met, which is the only thing a query can act on.
    """

    def test_the_honest_skips_carry_four_distinct_reason_codes(self):
        import gate_outcome

        codes = {
            gate_outcome.REASON_NO_DATABASE,
            gate_outcome.REASON_NO_INSTRUCTION_FILE,
            gate_outcome.REASON_NO_DYNAMIC_BLOCK,
            gate_outcome.REASON_EMPTY_KNOWLEDGE_BASE,
        }
        assert len(codes) == 4, "four empty states, four codes — not one code wearing four names"
        assert gate_outcome.REASON_RUNNER_ERROR not in codes

    @pytest.mark.parametrize(
        "case",
        ["no_database", "no_claudemd", "empty_knowledge_base"],
    )
    def test_an_honest_skip_does_not_block_and_says_which_one(self, case, monkeypatch, tmp_path):
        import gate_outcome

        if case == "no_database":
            import project_config

            empty = tmp_path / ".tausik"
            empty.mkdir()
            monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(empty))
            expected = gate_outcome.REASON_NO_DATABASE
        else:
            if not (REPO_ROOT / ".tausik" / "tausik.db").is_file():
                pytest.skip(DORMANT_WITHOUT_LIVE_DB)
            if case == "no_claudemd":
                import claudemd_state

                monkeypatch.setattr(claudemd_state, "resolve_claudemd", lambda d: None)
                expected = gate_outcome.REASON_NO_INSTRUCTION_FILE
            else:
                import service_knowledge_aggregates as ska

                monkeypatch.setattr(ska, "build_compact_memory_tail", lambda be: [])
                expected = gate_outcome.REASON_EMPTY_KNOWLEDGE_BASE

        outcome = run_claudemd_state_gate()
        assert outcome.outcome == gate_outcome.NOT_APPLICABLE
        assert outcome.reason_code == expected
        assert not outcome.blocks, "an empty project is not at fault for being empty"
        assert outcome.legacy_passed, "AC2: the honest skips stay passes for every old reader"


class TestTheReceiptForTheMeasuredFaultCarriesNonExecution:
    """AC4: reproduce #192 exactly — a database whose schema is NEWER than the
    code — and follow it all the way to the stored `gate_runs` row.

    Not a unit test of the gate's return value: the defect was in what got
    SIGNED, so the assertion is made on the row that `record_gate_runs` writes,
    reached through the real `run_gates` over the real registry entry.
    """

    def _project_with_a_future_schema(self, tmp_path):
        """A .tausik/ whose tausik.db announces a schema no code can read."""
        import sqlite3

        import backend_init

        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir()
        (tmp_path / "CLAUDE.md").write_text("# stub\n", encoding="utf-8")
        db = tausik_dir / "tausik.db"
        conn = sqlite3.connect(str(db))
        # `meta`, key='schema_version' — where backend_init.init_schema actually
        # reads the version from. Written as one row and nothing else, so the
        # guard is the FIRST thing the backend meets, exactly as in #192.
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(backend_init.SCHEMA_VERSION + 1),),
        )
        conn.commit()
        conn.close()
        return tausik_dir

    def test_a_database_newer_than_the_code_is_signed_as_cannot_run(self, monkeypatch, tmp_path):
        import sqlite3

        import gate_outcome
        import project_config
        from gate_run_record import record_gate_runs

        tausik_dir = self._project_with_a_future_schema(tmp_path)
        monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(tausik_dir))

        # Only the gate under test, run by the real runner — not a hand-built
        # result dict, which would prove the test equals itself.
        spec = None
        for g in project_config.get_gates_for_trigger("commit", project_config.load_config()):
            if g.get("name") == "claudemd_state_drift":
                spec = g
        assert spec is not None, "the gate is not wired into the commit trigger"
        monkeypatch.setattr("gate_runner.get_gates_for_trigger", lambda trigger, cfg=None: [spec])

        all_passed, results = run_gates("commit", [])
        assert len(results) == 1
        row_source = results[0]
        assert row_source["outcome"] == gate_outcome.COULD_NOT_RUN, (
            "this is #192 verbatim: the gate said 'schema is newer than code' and "
            f"the run was recorded as {row_source['outcome']}"
        )
        assert row_source["reason_code"] == gate_outcome.REASON_RUNNER_ERROR
        # Pinned to the fault that was actually measured, not to "some error":
        # the gate must have failed on the version guard, or this test is
        # reproducing a different bug than the one it is named for.
        assert "is newer than code" in row_source["output"]
        assert not all_passed, "severity=block plus no evidence must not certify"

        # ...and that is what reaches the table a receipt is read from.
        # The REAL table definition, imported rather than retyped: a test that
        # invents its own gate_runs proves nothing about the one a receipt is
        # read from.
        sink = sqlite3.connect(":memory:")
        sink.executescript(GATE_RUNS_SQL)
        record_gate_runs(
            sink,
            verification_run_id=None,
            task_slug="ac4",
            trigger="commit",
            gate_results=results,
        )
        stored = sink.execute(
            "SELECT outcome, reason_code, passed, skipped FROM gate_runs"
        ).fetchone()
        sink.close()
        assert stored == (
            gate_outcome.COULD_NOT_RUN,
            gate_outcome.REASON_RUNNER_ERROR,
            0,
            0,
        ), "the stored row is the evidence; before this task it read ('PASSED', '', 1, 0)"


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
