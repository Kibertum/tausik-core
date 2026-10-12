"""A file already read and unchanged is not paid for twice — inside a window.

MEASURED BEFORE BUILT (session #229, all 42 transcripts). 285 Read calls with a
path; 111 repeats of a path already read in the same conversation; 43 of those
after an Edit/Write, hence legitimate; 68 avoidable. Gap between repeats: median
4, p75 58, p90 187. A 20-call window covers 69.4% of them.

THE PRIZE IS NAMED, NOT IMPLIED. Read accounts for 370,213 of 17,896,506 tokens
of context growth — 2.07%. Eliminating every read would save that much; this
mechanism targets ~0.49%. Most re-reading in this corpus bypasses the Read tool
entirely: 2,196 genuine file reads live inside Bash commands with 604 avoidable
repeats (~3.1%). Covering those would mean blocking a call after parsing
arbitrary shell, and this project has an open owner-held defect showing that
shell parsing for gating misfires here. So the mechanism covers what it can
prove, and its ceiling is written down instead of being left to the reader.

THE WINDOW IS THE SAFETY, NOT THE SAVING. Beyond it a deny would be a silent data
cut: content read 400 calls ago may have left the context through compaction, and
refusing to re-read hands the agent an absence it cannot detect. Every
uncertainty in `decide` resolves to ALLOW.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_HOOKS = _REPO / "scripts" / "hooks"
sys.path.insert(0, str(_HOOKS))
sys.path.insert(0, str(_REPO / "scripts"))

from read_ledger import (  # noqa: E402
    DEFAULT_WINDOW_CALLS,
    decide,
    fingerprint,
    is_enabled,
    unchanged,
)

CROSSCUTTING_SCOPE = ["scripts/hooks/read_ledger.py", "scripts/hooks/read_ledger_gate.py"]

_GATE = _HOOKS / "read_ledger_gate.py"


def _ledger(calls: int, call_no: int = 5, **fp) -> dict:
    base = {"size": 3, "sha256": "x" * 64, "mtime": 1.0}
    base.update(fp)
    base["call_no"] = call_no
    return {"session_id": 1, "calls": calls, "files": {"a": base}}


def _now(**over) -> dict:
    base = {"size": 3, "sha256": "x" * 64, "mtime": 1.0}
    base.update(over)
    return base


class TestTheDecisionRefusesOnlyWhatItCanProve:
    def test_unchanged_inside_the_window_is_denied(self):
        deny, reason = decide(_ledger(10), "a", _now(), 20)
        assert deny
        assert "call #5" in reason

    def test_a_changed_file_passes(self):
        """AC7: the second read of a file that MOVED must go through."""
        deny, reason = decide(_ledger(10), "a", _now(size=4, sha256="y" * 64), 20)
        assert not deny
        assert "changed" in reason

    def test_beyond_the_window_passes(self):
        """AC7 / AC5: the compaction case. Far enough back, the content may be
        gone from the context, and a deny would be a silent cut."""
        deny, reason = decide(_ledger(100), "a", _now(), 20)
        assert not deny
        assert "beyond the 20-call window" in reason

    def test_a_file_never_read_passes(self):
        deny, _ = decide(_ledger(10), "some-other-path", _now(), 20)
        assert not deny

    def test_an_unfingerprintable_file_passes(self):
        """Unknown resolves to allow. Always."""
        deny, reason = decide(_ledger(10), "a", None, 20)
        assert not deny
        assert "not readable" in reason

    def test_exactly_at_the_window_edge_is_still_denied(self):
        """The boundary is stated, so it is tested rather than assumed."""
        deny, _ = decide(_ledger(25), "a", _now(), 20)  # distance 20
        assert deny
        deny, _ = decide(_ledger(26), "a", _now(), 20)  # distance 21
        assert not deny


class TestMtimeAndHashAreBothConsulted:
    """AC2: each lies on its own, so neither decides alone."""

    def test_same_hash_but_different_mtime_counts_as_unchanged(self):
        """A checkout restores identical bytes with a new mtime. Trusting mtime
        alone would let a pointless re-read through."""
        assert unchanged(
            {"size": 3, "sha256": "a" * 64, "mtime": 1.0},
            {"size": 3, "sha256": "a" * 64, "mtime": 999.0},
        )

    def test_same_mtime_but_different_hash_counts_as_changed(self):
        assert not unchanged(
            {"size": 3, "sha256": "a" * 64, "mtime": 1.0},
            {"size": 3, "sha256": "b" * 64, "mtime": 1.0},
        )

    def test_different_size_is_changed_without_hashing(self):
        assert not unchanged(
            {"size": 3, "sha256": None, "mtime": 1.0}, {"size": 9, "sha256": None, "mtime": 1.0}
        )

    def test_one_side_unhashed_is_not_demonstrated(self):
        """A hash on one side only proves nothing; the read goes through."""
        assert not unchanged(
            {"size": 3, "sha256": "a" * 64, "mtime": 1.0}, {"size": 3, "sha256": None, "mtime": 1.0}
        )

    def test_both_unhashed_falls_back_to_mtime(self):
        assert unchanged(
            {"size": 3, "sha256": None, "mtime": 1.0}, {"size": 3, "sha256": None, "mtime": 1.0}
        )

    def test_fingerprint_of_a_real_file_carries_all_three(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hello", encoding="utf-8")
        fp = fingerprint(str(f))
        assert fp is not None
        assert fp["size"] == 5 and fp["sha256"] and fp["mtime"] > 0
        assert fingerprint(str(tmp_path / "missing.txt")) is None


class TestTheWindowIsAMeasuredNumber:
    def test_the_default_window_matches_what_was_measured(self):
        """20 covers 69.4% of this project's Read repeats and 65.6% of its Bash
        ones. A window justified by nothing is what AC5 forbids shipping.

        The coverage arithmetic is pinned alongside the constant, so a future
        edit that moves the window has to move the claim with it instead of
        leaving a number whose justification quietly stopped applying.
        """
        assert DEFAULT_WINDOW_CALLS == 20
        read_gaps_within_20 = 77  # of 111 measured Read repeats
        assert round(100 * read_gaps_within_20 / 111, 1) == 69.4
        bash_gaps_within_20 = 495  # of 754 measured Bash repeats
        assert round(100 * bash_gaps_within_20 / 754, 1) == 65.6


class TestOffByDefaultMeansNothingHappens:
    """AC3 and AC8: proven by running it, not by reading the code."""

    def _run(self, project: Path, payload: dict, env: dict | None = None):
        environ = dict(os.environ)
        environ.pop("TAUSIK_SKIP_HOOKS", None)
        environ["CLAUDE_PROJECT_DIR"] = str(project)
        environ.update(env or {})
        return subprocess.run(
            [sys.executable, str(_GATE)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(project),
            env=environ,
            timeout=60,
        )

    def _project(self, tmp_path: Path, enabled: bool | None) -> Path:
        (tmp_path / ".tausik").mkdir(exist_ok=True)
        if enabled is not None:
            (tmp_path / ".tausik" / "config.json").write_text(
                json.dumps({"read_ledger": {"enabled": enabled}}), encoding="utf-8"
            )
        return tmp_path

    def test_absent_config_is_off(self, tmp_path):
        project = self._project(tmp_path, None)
        assert is_enabled(str(project)) is False

    def test_when_off_no_ledger_file_is_ever_created(self, tmp_path):
        project = self._project(tmp_path, None)
        target = project / "f.txt"
        target.write_text("x", encoding="utf-8")
        for _ in range(3):
            proc = self._run(
                project, {"tool_name": "Read", "tool_input": {"file_path": str(target)}}
            )
            assert proc.returncode == 0
        assert not (project / ".tausik" / "read_ledger.json").exists(), (
            "the hook wrote a ledger while disabled — 'off' must mean off"
        )

    def test_when_on_it_denies_the_second_identical_read(self, tmp_path):
        project = self._project(tmp_path, True)
        target = project / "f.txt"
        target.write_text("x" * 100, encoding="utf-8")
        payload = {"tool_name": "Read", "tool_input": {"file_path": str(target)}}
        first = self._run(project, payload)
        assert first.returncode == 0, first.stderr
        second = self._run(project, payload)
        assert second.returncode == 2
        assert "already read in this session" in second.stderr

    def test_a_changed_file_is_allowed_on_the_second_read(self, tmp_path):
        """AC7 end to end, through the real hook rather than the pure function."""
        project = self._project(tmp_path, True)
        target = project / "f.txt"
        target.write_text("first", encoding="utf-8")
        payload = {"tool_name": "Read", "tool_input": {"file_path": str(target)}}
        assert self._run(project, payload).returncode == 0
        target.write_text("second, quite different", encoding="utf-8")
        assert self._run(project, payload).returncode == 0

    def test_the_override_lets_one_call_through_and_says_so(self, tmp_path):
        project = self._project(tmp_path, True)
        target = project / "f.txt"
        target.write_text("x", encoding="utf-8")
        payload = {"tool_name": "Read", "tool_input": {"file_path": str(target)}}
        self._run(project, payload)
        blocked = self._run(project, payload)
        assert blocked.returncode == 2
        assert "TAUSIK_READ_LEDGER_OVERRIDE" in blocked.stderr, "a wall with no door"
        allowed = self._run(project, payload, env={"TAUSIK_READ_LEDGER_OVERRIDE": "1"})
        assert allowed.returncode == 0

    def test_a_partial_read_is_never_denied(self, tmp_path):
        """offset/limit asks for a slice that was never in the context."""
        project = self._project(tmp_path, True)
        target = project / "f.txt"
        target.write_text("x" * 100, encoding="utf-8")
        whole = {"tool_name": "Read", "tool_input": {"file_path": str(target)}}
        slice_ = {"tool_name": "Read", "tool_input": {"file_path": str(target), "offset": 10}}
        self._run(project, whole)
        assert self._run(project, slice_).returncode == 0

    def test_another_tool_is_untouched(self, tmp_path):
        project = self._project(tmp_path, True)
        proc = self._run(project, {"tool_name": "Bash", "tool_input": {"command": "cat f.txt"}})
        assert proc.returncode == 0
        assert not (project / ".tausik" / "read_ledger.json").exists()

    def test_malformed_payloads_do_not_break_the_call_they_guard(self, tmp_path):
        project = self._project(tmp_path, True)
        for raw in ("", "not json", "[]", '{"tool_name": "Read"}'):
            proc = subprocess.run(
                [sys.executable, str(_GATE)],
                input=raw,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(project),
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
                timeout=60,
            )
            assert proc.returncode == 0, f"died on {raw!r}: {proc.stderr[-200:]}"


class TestTheSavingIsCountedNotClaimed:
    """AC4: a claim of economy without a counter is forbidden."""

    def test_each_refusal_increments_a_counter_in_the_ledger(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "config.json").write_text(
            json.dumps({"read_ledger": {"enabled": True}}), encoding="utf-8"
        )
        target = tmp_path / "f.txt"
        target.write_text("x", encoding="utf-8")
        payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": str(target)}})
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
        env.pop("TAUSIK_SKIP_HOOKS", None)
        for _ in range(3):
            subprocess.run(
                [sys.executable, str(_GATE)],
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(tmp_path),
                env=env,
                timeout=60,
            )
        ledger = json.loads((tmp_path / ".tausik" / "read_ledger.json").read_text(encoding="utf-8"))
        assert ledger["saved_reads"] == 2, "two of three reads were refused and must be counted"
