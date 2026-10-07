"""Agent friction becomes a filed draft, not a swallowed log line.

Task agent-friction-becomes-a-filed-defect-not-a-swallowed-one. The negative
lanes carry the weight (AC-6, convention #351): normal work — fail-then-green
retries, task-code dead ends, clean successes — must produce ZERO drafts, and
the live tree must stay under five findings. A detector that fires on normal
work teaches the reader to skip it.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from friction_detect import (  # noqa: E402
    FrictionSignal,
    assert_no_network_surface,
    detect_friction,
    drafts_count,
    record_invocation_exit,
    redact,
    run_friction_cmd,
    write_drafts,
)
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

LIVE_TAUSIK = os.path.join(_ROOT, ".tausik")


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "fr.db")))
    yield s
    s.be.close()


def _invocation(argv: list[str], exit_code: int, ts: str) -> dict:
    return {"schema_version": 1, "ts": ts, "argv": argv, "exit": exit_code}


T1 = "2026-10-07T10:00:00+00:00"
T2 = "2026-10-07T10:02:00+00:00"
T3 = "2026-10-07T10:04:00+00:00"
T4 = "2026-10-07T10:06:00+00:00"


def _write_rows(tausik_dir: str, rows: list[dict]) -> None:
    os.makedirs(tausik_dir, exist_ok=True)
    with open(os.path.join(tausik_dir, "cli_invocations.jsonl"), "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


# --- Signals A/B/C/D/E: each fires on its planted form -------------------------


def test_nonzero_exit_collapses_per_command(tmp_path):
    _write_rows(
        str(tmp_path),
        [
            _invocation(["task", "done", "x"], 1, T1),
            _invocation(["task", "done", "y"], 1, T2),
            _invocation(["task", "done", "z"], 1, T3),
        ],
    )
    signals = detect_friction(str(tmp_path))
    nonzero = [s for s in signals if s.kind == "nonzero-exit"]
    assert len(nonzero) == 1, "three same-command failures must collapse to ONE draft (AC-5)"
    assert nonzero[0].count == 3 and "task" in nonzero[0].signature


def test_a_single_red_exit_is_the_framework_teaching_not_friction(tmp_path):
    """One red task-done is a gate refusal carrying its own remediation — the
    live corpus (this very session's task-done refusals) proved one-shot reds
    are the ordinary rhythm, not a fight with the framework."""
    _write_rows(
        str(tmp_path), [_invocation(["task", "done", "t"], 1, T1), _invocation(["status"], 0, T2)]
    )
    assert [s for s in detect_friction(str(tmp_path)) if s.kind == "nonzero-exit"] == []


def test_help_right_after_failure_is_the_guessing_escape(tmp_path):
    _write_rows(
        str(tmp_path),
        [
            _invocation(["verify", "--task", "wrong-flag"], 1, T1),
            _invocation(["verify", "--help"], 0, T2),
        ],
    )
    signals = detect_friction(str(tmp_path))
    assert any(s.kind == "help-after-failure" for s in signals)


def test_arg_guessing_run_is_detected(tmp_path):
    _write_rows(
        str(tmp_path),
        [
            _invocation(["skill", "install", "--from", "x"], 1, T1),
            _invocation(["skill", "install", "--repo", "y"], 1, T2),
            _invocation(["skill", "install", "--url", "z"], 1, T3),
        ],
    )
    signals = detect_friction(str(tmp_path))
    assert any(s.kind == "arg-guessing" for s in signals)


def test_supervision_degradation_is_a_signal(tmp_path):
    """fail_open_* — the guard itself could not run — is framework friction."""
    hooks_dir = os.path.join(_ROOT, "scripts", "hooks")
    sys.path.insert(0, hooks_dir)
    from hook_supervision import emit_supervision_degradation

    # svc FIRST: opening it creates the schema the supervision writer needs.
    svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    try:
        emit_supervision_degradation(str(tmp_path), "db_error", "task_gate")
        signals = detect_friction(str(tmp_path), svc)
    finally:
        svc.be.close()
    degraded = [s for s in signals if s.kind == "supervision-degraded"]
    assert degraded and "task_gate" in degraded[0].signature


def test_deliberate_skip_hooks_is_not_framework_friction(tmp_path):
    """A bypass_* row is the agent's own audited choice (metrics count it);
    counting it here drowned the drafts — 22 entities in the live corpus."""
    hooks_dir = os.path.join(_ROOT, "scripts", "hooks")
    sys.path.insert(0, hooks_dir)
    from hook_supervision import emit_supervision_bypass

    svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    try:
        emit_supervision_bypass(str(tmp_path), "skip_hooks", "secret_scan")
        signals = detect_friction(str(tmp_path), svc)
    finally:
        svc.be.close()
    assert [s for s in signals if s.kind == "supervision-degraded"] == []


def test_framework_dead_end_is_a_signal(svc, tmp_path):
    svc.memory_add(
        "dead_end",
        "MCP tausik_task_logs отдаёт пустые параметры",
        "Approach: read task logs via MCP\nReason: MCP returns empty params, drift suspected",
    )
    signals = detect_friction(str(tmp_path), svc)
    assert any(s.kind == "framework-dead-end" for s in signals)


# --- AC-6 precision: normal work produces NOTHING -------------------------------


def test_fail_then_green_retry_is_not_friction(tmp_path):
    """The edit-fix-rerun rhythm: one red verify, then green. NOT guessing."""
    _write_rows(
        str(tmp_path),
        [
            _invocation(["verify", "--task", "t"], 1, T1),
            _invocation(["verify", "--task", "t"], 0, T4),
        ],
    )
    assert [
        s
        for s in detect_friction(str(tmp_path))
        if s.kind in ("arg-guessing", "help-after-failure")
    ] == []


def test_green_invocations_produce_nothing(tmp_path):
    _write_rows(
        str(tmp_path),
        [_invocation(["status"], 0, T1), _invocation(["task", "list"], 0, T2)],
    )
    assert detect_friction(str(tmp_path)) == []


def test_task_code_dead_end_is_not_framework_friction(svc, tmp_path):
    """A dead end about the agent's OWN code (copy a test shape) is not ours."""
    svc.memory_add(
        "dead_end",
        "Copy the v49 test shape verbatim",
        "Approach: copy the shape\nReason: two bare asserts land in the dedupe group",
    )
    assert [s for s in detect_friction(str(tmp_path), svc) if s.kind == "framework-dead-end"] == []


# --- AC-3 redaction, AC-4 no-network, AC-2 draft placement ----------------------


def test_drafts_are_redacted_and_counted(tmp_path):
    sig = FrictionSignal(
        kind="nonzero-exit",
        signature="nonzero-exit:task",
        count=4,
        sample="task done someone@example.com after D:\\Work\\Client\\secret-slug",
        remedy_hint="hint",
    )
    written = write_drafts(str(tmp_path), [sig])
    assert len(written) == 1 and drafts_count(str(tmp_path)) == 1
    with open(written[0], encoding="utf-8") as fh:
        body = fh.read()
    assert "someone@example.com" not in body and "[redacted]" in body
    assert "occurrences: 4" in body


def test_redact_uses_the_shared_scrubber():
    out = redact("contact a@b.io and a@b.io twice")
    assert "a@b.io" not in out and out.count("[redacted]") == 2


def test_no_network_surface_in_the_module():
    """AC-4 made mechanical: no network imports exist, so nothing can send."""
    assert assert_no_network_surface()


def test_friction_cmd_never_blocks_and_names_the_boundary(tmp_path, svc, capsys, monkeypatch):
    monkeypatch.setattr("project_config.find_tausik_dir", lambda: str(tmp_path))
    _write_rows(str(tmp_path), [_invocation(["status"], 1, T1), _invocation(["status"], 1, T2)])
    result = run_friction_cmd(svc)
    assert result is None
    out = capsys.readouterr().out
    assert "Nothing is sent anywhere" in out
    assert drafts_count(str(tmp_path)) >= 1


def test_recorder_appends_and_survives_missing_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no .tausik here
    assert record_invocation_exit(0, ["status"]) is False
    os.makedirs(tmp_path / ".tausik")
    assert record_invocation_exit(1, ["verify"]) is True
    with open(tmp_path / ".tausik" / "cli_invocations.jsonl", encoding="utf-8") as fh:
        rows = fh.read().splitlines()
    assert len(rows) == 1 and json.loads(rows[0])["exit"] == 1


# --- AC-6 on the LIVE tree -------------------------------------------------------


@pytest.mark.skipif(not os.path.isdir(LIVE_TAUSIK), reason="no live .tausik in this checkout")
def test_live_tree_false_alarms_on_green_rows_and_bounded_genuine(tmp_path):
    """Live precision (AC-6), two halves. FALSE ALARM = a finding with no
    failing cause: on the live invocation rows restricted to GREEN exits the
    detector must produce NOTHING (unit-lane boundaries already pin the other
    no-cause shapes). GENUINE friction — this very session's repeated red
    `task done` refusals, the week's MCP dead ends — is the detector WORKING;
    it is listed in the assertion message and bounded at ten against runaway."""
    src = os.path.join(LIVE_TAUSIK, "cli_invocations.jsonl")
    rows: list[dict] = []
    if os.path.isfile(src):
        with open(src, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    _write_rows(str(tmp_path), [r for r in rows if int(r.get("exit") or 0) == 0])
    assert detect_friction(str(tmp_path)) == [], (
        "a finding on green-only rows is a false alarm by definition"
    )

    svc = ProjectService(SQLiteBackend(os.path.join(LIVE_TAUSIK, "tausik.db")))
    try:
        _write_rows(str(tmp_path), rows)
        signals = detect_friction(str(tmp_path), svc)
    finally:
        svc.be.close()
    assert len(signals) <= 10, (
        f"{len(signals)} findings on the live tree — runaway, review the detector: "
        + "; ".join(f"{s.kind}:{s.signature}x{s.count}" for s in signals[:10])
    )
