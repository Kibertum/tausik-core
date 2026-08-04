"""l26-complexity-self-declared: an understated complexity is VISIBLE at close.

The pure `understatement` decision is pinned exhaustively (declared vs implied by
touched-file count), then the task_done integration confirms the detection emits
a supervision event and surfaces a warning — and stays SILENT for honestly
declared tasks so it adds no false noise.
"""

from __future__ import annotations

import os
import sqlite3
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from complexity_understatement import (  # noqa: E402
    behaviour_bearing_files,
    implied_complexity,
    understatement,
)


def _files(n: int) -> list[str]:
    return [f"scripts/f{i}.py" for i in range(n)]


class TestImpliedComplexity:
    def test_boundaries(self):
        # <=3 files -> simple; 4..10 -> medium; >10 -> complex.
        assert implied_complexity(0) == "simple"
        assert implied_complexity(3) == "simple"
        assert implied_complexity(4) == "medium"
        assert implied_complexity(10) == "medium"
        assert implied_complexity(11) == "complex"


class TestUnderstatement:
    def test_simple_touching_many_is_understated(self):
        u = understatement("simple", _files(4))
        assert u == {
            "declared": "simple",
            "implied": "medium",
            "file_count": 4,
            "declared_count": 4,
        }

    def test_simple_touching_a_lot_implies_complex(self):
        u = understatement("simple", _files(11))
        assert u["implied"] == "complex"

    def test_honest_simple_is_none(self):
        assert understatement("simple", _files(2)) is None
        assert understatement("simple", []) is None

    def test_unset_complexity_treated_as_simple(self):
        # An unset complexity dodges the same gates as 'simple' — same scrutiny.
        assert understatement(None, _files(5)) == {
            "declared": "simple",
            "implied": "medium",
            "file_count": 5,
            "declared_count": 5,
        }
        assert understatement("", _files(2)) is None

    def test_unknown_label_treated_as_simple(self):
        assert understatement("weird", _files(4)) is not None

    def test_medium_within_ceiling_is_none(self):
        assert understatement("medium", _files(10)) is None

    def test_medium_touching_a_lot_is_understated(self):
        u = understatement("medium", _files(11))
        assert u == {
            "declared": "medium",
            "implied": "complex",
            "file_count": 11,
            "declared_count": 11,
        }

    def test_complex_is_never_understated(self):
        assert understatement("complex", _files(50)) is None

    def test_none_entries_are_ignored_in_count(self):
        assert understatement("simple", ["a.py", "", "b.py"]) is None  # 2 real files


# --- What the file count is allowed to count ---------------------------------

# The closure that made this measurable: 13 declared files, 9 of them able to
# carry a behaviour change. Declared 'medium', warned as 'complex'.
_LIVE_CLOSURE_FILES = [
    "scripts/gate_command_runner.py",
    "scripts/gate_runner.py",
    "scripts/gate_test_resolver.py",
    "pyproject.toml",
    "tests/test_gate_command_runner.py",
    "tests/test_gate_test_resolver.py",
    "tests/test_pytest_hang_guard.py",
    "docs/_generated/constants.json",
    "docs/ru/agent-contract.md",
    "README.md",
    "README.ru.md",
    "CHANGELOG.md",
    "CHANGELOG.ru.md",
]


class TestBehaviourBearingFiles:
    """complexity-heuristic-counts-doc-mirrors: framework files ride along on EVERY task."""

    def test_ceremony_files_do_not_count(self):
        """Both CHANGELOGs, CLAUDE.md and its synced AGENTS.md sibling are mandated."""
        assert (
            behaviour_bearing_files(["CHANGELOG.md", "CHANGELOG.ru.md", "CLAUDE.md", "AGENTS.md"])
            == []
        )

    def test_agents_md_is_ceremony_because_update_claudemd_writes_it(self):
        """AGENTS.md is written from the same source as CLAUDE.md on every close;
        touching it carries no more behaviour than touching CLAUDE.md."""
        assert behaviour_bearing_files(["AGENTS.md"]) == []
        # It must not inflate a real change: AGENTS.md + one real file == 1 bearing.
        assert behaviour_bearing_files(["AGENTS.md", "scripts/real.py"]) == ["scripts/real.py"]

    def test_the_sibling_ceremony_entry_comes_from_the_producer(self):
        """The name lives in claudemd_writer; hand-listing a copy is how the two
        drift. Assert the ceremony set is keyed off the producer's constant."""
        import complexity_understatement as cu
        from claudemd_writer import CLAUDEMD_SIBLING_BASENAME

        assert CLAUDEMD_SIBLING_BASENAME.lower() in cu._CEREMONY_FILES

    def test_a_task_of_pure_ceremony_is_never_understated(self):
        """Zero bearing files cannot imply anything above 'simple'."""
        assert (
            understatement("simple", ["CHANGELOG.md", "CHANGELOG.ru.md", "CLAUDE.md", "AGENTS.md"])
            is None
        )

    def test_generated_artefacts_do_not_count(self):
        assert behaviour_bearing_files(["docs/_generated/constants.json"]) == []

    def test_generated_artefacts_do_not_count_with_windows_separators(self):
        """`git status` on Windows and a hand-typed path disagree about slashes."""
        assert behaviour_bearing_files([r"docs\_generated\constants.json"]) == []

    def test_a_translation_pair_counts_once(self):
        assert len(behaviour_bearing_files(["docs/ru/x.md", "docs/en/x.md"])) == 1
        assert len(behaviour_bearing_files(["README.md", "README.ru.md"])) == 1

    def test_a_lone_mirror_still_counts(self):
        """Editing only the translation is work; dropping it would hide it."""
        assert behaviour_bearing_files(["README.ru.md"]) == ["README.ru.md"]
        assert behaviour_bearing_files(["docs/ru/x.md"]) == ["docs/ru/x.md"]

    def test_duplicates_do_not_double_count(self):
        assert behaviour_bearing_files(["scripts/a.py", "scripts/a.py"]) == ["scripts/a.py"]

    def test_empty_and_none_are_zero_not_an_error(self):
        assert behaviour_bearing_files(None) == []
        assert behaviour_bearing_files([]) == []
        assert behaviour_bearing_files(["", None]) == []  # type: ignore[list-item]

    def test_real_code_still_counts(self):
        """The filter must not be a way to make a big change look small."""
        many = [f"scripts/hooks/h{i}.py" for i in range(12)]
        assert len(behaviour_bearing_files(many)) == 12
        assert understatement("simple", many)["implied"] == "complex"


class TestTheClosureThatExposedIt:
    def test_the_live_closure_stops_being_flagged(self):
        """AC-4 dogfood: 13 declared -> 9 bearing -> 'medium', which is what it said."""
        assert len(_LIVE_CLOSURE_FILES) == 13
        assert len(behaviour_bearing_files(_LIVE_CLOSURE_FILES)) == 9
        assert understatement("medium", _LIVE_CLOSURE_FILES) is None

    def test_the_warning_names_both_numbers(self):
        """ "Touched 9 files" about a 13-file `git status` reads like a broken tool."""
        u = understatement("simple", _LIVE_CLOSURE_FILES)
        assert u["file_count"] == 9
        assert u["declared_count"] == 13

    def test_a_genuinely_understated_closure_is_still_caught(self):
        """AC-3: the advisory must survive its own false-positive cure.

        Real history — `push-gate-ors-two-dialects-and-false-blocks` declared
        'simple' while changing four hook modules. Nine declared files, six of
        them bearing: still 'medium', still flagged.
        """
        files = [
            "scripts/hooks/git_push_gate.py",
            "scripts/hooks/shell_channel.py",
            "scripts/hooks/bash_write_parse.py",
            "scripts/hooks/pwsh_write_parse.py",
            "tests/test_powershell_channel.py",
            "docs/ru/enforcement-coverage.md",
            "docs/en/enforcement-coverage.md",
            "CHANGELOG.md",
            "CHANGELOG.ru.md",
        ]
        u = understatement("simple", files)
        assert u is not None
        assert (u["file_count"], u["declared_count"]) == (6, 9)
        assert u["implied"] == "medium"


# --- Integration through the real task_done flow -----------------------------


def _supervision_events(be) -> list[tuple[str, str]]:
    row = be._conn.execute("PRAGMA database_list").fetchone()
    conn = sqlite3.connect(row[2])
    try:
        return conn.execute(
            "SELECT entity_id, action FROM events WHERE entity_type='supervision' ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


class TestMetricSeparation:
    """A detection (supervision WORKED) must never be counted as a bypass
    (supervision was switched off) — they are opposite meanings (l26 review)."""

    def test_bypass_and_detection_counted_separately(self, tmp_path):
        from project_backend import SQLiteBackend

        be = SQLiteBackend(str(tmp_path / "m.db"))
        be.event_add("supervision", "hook", "bypass_skip_hooks")
        be.event_add("supervision", "t1", "complexity_understated", "files=5")
        assert be.supervision_bypasses_summary() == {
            "total": 1,
            "by_action": {"bypass_skip_hooks": 1},
        }
        assert be.supervision_detections_summary() == {
            "total": 1,
            "by_action": {"complexity_understated": 1},
        }
        be.close()


class TestTaskDoneIntegration:
    def _make(self, tmp_path, monkeypatch, complexity):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TAUSIK_QUIET", "1")
        svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
        svc.task_add(None, "t-cx", "Complexity task")
        svc.task_update(
            "t-cx",
            goal="g",
            acceptance_criteria="1. ok\n2. errors on bad input",
            scope="x.py",
            rollback_plan="git revert",
            complexity=complexity,
        )
        svc.task_start("t-cx")
        return svc

    def test_understated_simple_emits_event_and_warns(self, tmp_path, monkeypatch):
        svc = self._make(tmp_path, monkeypatch, "simple")
        try:
            result = svc.task_done(
                "t-cx", _files(5), True, True, evidence="AC verified: 1. ok 2. ok"
            )
            assert "COMPLEXITY UNDERSTATED" in result
            assert svc.be.task_get("t-cx")["status"] == "done"  # advisory, not blocking
            assert _supervision_events(svc.be) == [("t-cx", "complexity_understated")]
        finally:
            svc.be.close()

    def test_honest_simple_is_silent(self, tmp_path, monkeypatch):
        svc = self._make(tmp_path, monkeypatch, "simple")
        try:
            result = svc.task_done(
                "t-cx", _files(2), True, True, evidence="AC verified: 1. ok 2. ok"
            )
            assert "COMPLEXITY UNDERSTATED" not in result
            assert svc.be.task_get("t-cx")["status"] == "done"
            assert _supervision_events(svc.be) == []
        finally:
            svc.be.close()

    def test_a_broken_filter_does_not_block_close(self, tmp_path, monkeypatch):
        """The new filter is inside the fail-open envelope too (gotcha #271).

        `behaviour_bearing_files` is more code than the count it replaced, so it
        is more able to raise. A path shape nobody anticipated must cost the
        advisory, never the closure.
        """
        import complexity_understatement as cu

        svc = self._make(tmp_path, monkeypatch, "simple")
        monkeypatch.setattr(
            cu, "behaviour_bearing_files", lambda _f: (_ for _ in ()).throw(ValueError("bad path"))
        )
        try:
            result = svc.task_done(
                "t-cx", _files(5), True, True, evidence="AC verified: 1. ok 2. ok"
            )
            assert svc.be.task_get("t-cx")["status"] == "done"
            assert "COMPLEXITY UNDERSTATED" not in result
        finally:
            svc.be.close()

    def test_emit_failure_does_not_block_close(self, tmp_path, monkeypatch):
        """Fail-open (gotcha #271): a telemetry error must not crash the close."""
        svc = self._make(tmp_path, monkeypatch, "simple")

        real_event_add = svc.be.event_add

        def _boom(entity_type, *a, **k):
            if entity_type == "supervision":
                raise RuntimeError("db on fire")
            return real_event_add(entity_type, *a, **k)

        monkeypatch.setattr(svc.be, "event_add", _boom)
        try:
            result = svc.task_done(
                "t-cx", _files(5), True, True, evidence="AC verified: 1. ok 2. ok"
            )
            # The warning is still surfaced; only the event write failed, silently.
            assert "COMPLEXITY UNDERSTATED" in result
            assert svc.be.task_get("t-cx")["status"] == "done"
        finally:
            svc.be.close()
