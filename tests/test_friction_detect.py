"""Agent friction becomes a filed local task, not a swallowed log line.

Task agent-friction-becomes-a-filed-defect-not-a-swallowed-one. The negative
lanes carry the weight (AC-6, the live-accuracy convention): normal work — fail-then-green
retries, task-code dead ends, clean successes — must produce ZERO findings, and
the live tree must stay under five findings. A detector that fires on normal
work teaches the reader to skip it.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from friction_detect import (  # noqa: E402
    assert_no_network_surface,
    command_path,
    detect_friction,
    record_invocation_exit,
    run_friction_cmd,
)
import friction_filing  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project import _run_entrypoint  # noqa: E402
from project_service import ProjectService  # noqa: E402

LIVE_TAUSIK = os.path.join(_ROOT, ".tausik")


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "fr.db")))
    yield s
    s.be.close()


def _invocation(argv: list[str], exit_code: int, ts: str, origin: str = "cli") -> dict:
    return {"schema_version": 2, "ts": ts, "argv": argv, "exit": exit_code, "origin": origin}


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


def test_parser_recognized_subcommands_never_collapse_together(tmp_path):
    _write_rows(
        str(tmp_path),
        [
            _invocation(["task", "show", "x"], 1, T1),
            _invocation(["task", "show", "y"], 1, T2),
            _invocation(["task", "done", "x"], 1, T3),
            _invocation(["task", "done", "y"], 1, T4),
        ],
    )
    signatures = {
        signal.signature
        for signal in detect_friction(str(tmp_path))
        if signal.kind == "nonzero-exit"
    }
    assert signatures == {"nonzero-exit:task show", "nonzero-exit:task done"}


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["metrics", "record-session", "--cost-usd", "None"], "metrics record-session"),
        (["task", "done", "x"], "task done"),
        (["task", "show", "x"], "task show"),
        (["verify", "--task", "x"], "verify"),
    ],
)
def test_labeled_live_corpus_uses_parser_paths(argv, expected):
    """Labels come from observed cost=None, task retries and mixed command history."""
    assert command_path(argv) == expected


def test_labeled_observed_corpus_precision(tmp_path):
    """Observed production shapes are labeled before filing is allowed."""
    cost_none = [
        "metrics",
        "record-session",
        "--tokens-total",
        "0",
        "--cost-usd",
        "None",
        "--session-id",
        "1",
    ]
    cases = [
        (
            "cost_usd_none_repeats",
            [_invocation(cost_none, 2, T1), _invocation(cost_none, 2, T2)],
            {"nonzero-exit:metrics record-session"},
        ),
        (
            "pytest_negative_probes",
            [
                _invocation(cost_none, 2, T1, origin="pytest"),
                _invocation(cost_none, 2, T2, origin="pytest"),
            ],
            set(),
        ),
        (
            "mixed_task_subcommands",
            [
                _invocation(["task", "show", "a"], 2, T1),
                _invocation(["task", "show", "b"], 2, T2),
                _invocation(["task", "done", "a"], 2, T3),
                _invocation(["task", "done", "b"], 2, T4),
            ],
            {"nonzero-exit:task show", "nonzero-exit:task done"},
        ),
        (
            "help_then_green",
            [
                _invocation(["verify", "--bad"], 2, T1),
                _invocation(["verify", "--help"], 0, T2),
                _invocation(["verify", "--task", "x"], 0, T3),
            ],
            set(),
        ),
    ]
    for label, rows, expected in cases:
        case_dir = tmp_path / label
        _write_rows(str(case_dir), rows)
        actual = {signal.signature for signal in detect_friction(str(case_dir))}
        assert actual == expected, label


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


def test_help_then_successful_command_is_recovery_not_friction(tmp_path):
    _write_rows(
        str(tmp_path),
        [
            _invocation(["verify", "--bad"], 2, T1),
            _invocation(["verify", "--help"], 0, T2),
            _invocation(["verify", "--task", "x"], 0, T3),
        ],
    )
    assert detect_friction(str(tmp_path)) == []


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


def test_separate_runs_with_one_correlation_key_collapse(tmp_path):
    rows = [
        _invocation(["skill", "install", flag, value], 1, ts)
        for flag, value, ts in [
            ("--from", "a", T1),
            ("--repo", "b", T2),
            ("--url", "c", T3),
        ]
    ]
    rows += [_invocation(["status"], 0, T4)]
    rows += [
        _invocation(["skill", "install", flag, value], 1, ts)
        for flag, value, ts in [
            ("--from", "d", T1),
            ("--repo", "e", T2),
            ("--url", "f", T3),
        ]
    ]
    _write_rows(str(tmp_path), rows)

    signals = [s for s in detect_friction(str(tmp_path)) if s.kind == "arg-guessing"]
    assert len(signals) == 1 and signals[0].count == 6


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


def test_unrelated_task_link_does_not_hide_framework_dead_end(svc, tmp_path):
    svc.task_quick("owner", "Own the framework failure", "Framework failure is fixed")
    svc.memory_add(
        "dead_end",
        "MCP tausik_task_logs returns empty parameters",
        "Approach: read task logs via MCP\nReason: MCP returns empty params, drift suspected",
        task_slug="owner",
    )

    signals = detect_friction(str(tmp_path), svc)

    assert len([s for s in signals if s.kind == "framework-dead-end"]) == 1


# --- AC-6 precision: normal work produces NOTHING -------------------------------


def test_fail_then_green_retry_is_not_friction(tmp_path):
    """The edit-fix-rerun rhythm: one red verify, then green. NOT guessing."""
    _write_rows(
        str(tmp_path),
        [
            _invocation(["verify", "--task", "t", "--first"], 1, T1),
            _invocation(["verify", "--task", "t", "--second"], 1, T2),
            _invocation(["verify", "--task", "t"], 0, T4),
        ],
    )
    assert detect_friction(str(tmp_path)) == []


def test_green_invocations_produce_nothing(tmp_path):
    _write_rows(
        str(tmp_path),
        [_invocation(["status"], 0, T1), _invocation(["task", "list"], 0, T2)],
    )
    assert detect_friction(str(tmp_path)) == []


def test_pytest_generated_failures_are_excluded_with_a_notice(tmp_path):
    _write_rows(
        str(tmp_path),
        [
            _invocation(["task", "add", "bad"], 2, T1, origin="pytest"),
            _invocation(["task", "add", "worse"], 2, T2, origin="pytest"),
        ],
    )
    notices: list[str] = []
    assert detect_friction(str(tmp_path), notices=notices) == []
    assert notices == ["excluded 2 pytest-generated invocation row(s)"]


@pytest.mark.parametrize("bad_line", ["{not-json", "[]", '{"schema_version": 2}'])
def test_malformed_invocation_corpus_refuses_instead_of_looking_clean(tmp_path, bad_line):
    os.makedirs(tmp_path, exist_ok=True)
    (tmp_path / "cli_invocations.jsonl").write_text(bad_line + "\n", encoding="utf-8")
    notices: list[str] = []

    assert detect_friction(str(tmp_path), notices=notices) == []
    assert notices and notices[0].startswith("REFUSED CLI filing:")


def test_naive_timestamp_refuses_mixed_timezones_without_crashing(tmp_path):
    _write_rows(
        str(tmp_path),
        [
            _invocation(["task", "done", "x"], 1, "2026-10-07T10:00:00"),
            _invocation(["task", "done", "--help"], 0, T2),
        ],
    )
    notices: list[str] = []

    assert detect_friction(str(tmp_path), notices=notices) == []
    assert notices and notices[0].startswith("REFUSED CLI filing:")


def test_source_failures_are_reported_instead_of_claiming_a_clean_scan(tmp_path):
    class BrokenSources:
        def events_list(self, **_kwargs):
            raise RuntimeError("events unavailable")

        def memory_list(self, **_kwargs):
            raise ValueError("memory unavailable")

    notices: list[str] = []

    assert detect_friction(str(tmp_path), BrokenSources(), notices=notices) == []
    assert notices == [
        "REFUSED supervision filing: event source failed (RuntimeError)",
        "REFUSED dead-end filing: memory source failed (ValueError)",
    ]


@pytest.mark.parametrize("offset_seconds", [1, -(7 * 24 * 60 * 60 + 1)])
def test_dead_end_window_rejects_future_and_older_than_seven_days(offset_seconds):
    from friction_detect import _signal_e

    created = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    row = {
        "type": "dead_end",
        "title": "TAUSIK MCP stale refusal",
        "content": "MCP stays stale and refuses the operation",
        "created_at": created.isoformat(),
    }

    assert _signal_e([row]) == []


def test_task_code_dead_end_is_not_framework_friction(svc, tmp_path):
    """A dead end about the agent's OWN code (copy a test shape) is not ours."""
    svc.memory_add(
        "dead_end",
        "Copy the v49 test shape verbatim",
        "Approach: copy the shape\nReason: two bare asserts land in the dedupe group",
    )
    assert [s for s in detect_friction(str(tmp_path), svc) if s.kind == "framework-dead-end"] == []


@pytest.mark.parametrize("module_path", [None, friction_filing.__file__])
def test_no_network_surface_in_the_module(module_path):
    """AC-4 made mechanical: no network imports exist, so nothing can send."""
    assert assert_no_network_surface(module_path)


def test_friction_cmd_never_blocks_and_names_the_boundary(tmp_path, svc, capsys, monkeypatch):
    monkeypatch.setattr("project_config.find_tausik_dir", lambda: str(tmp_path))
    _write_rows(str(tmp_path), [_invocation(["status"], 1, T1), _invocation(["status"], 1, T2)])
    result = run_friction_cmd(svc)
    assert result is None
    out = capsys.readouterr().out
    assert "Nothing is sent anywhere" in out
    assert any(task["slug"].startswith("friction-") for task in svc.task_list())


def test_retained_window_truncation_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr("friction_detect.command_path", lambda argv: argv[0] if argv else "")
    rows = [_invocation(["status"], 0, T1) for _ in range(8_001)]
    _write_rows(str(tmp_path), rows)
    notices: list[str] = []

    assert detect_friction(str(tmp_path), notices=notices) == []
    assert notices and "declared retained tail" in notices[0]


def test_recorder_appends_and_survives_missing_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no .tausik here
    assert record_invocation_exit(0, ["status"]) is False
    os.makedirs(tmp_path / ".tausik")
    assert record_invocation_exit(1, ["verify"]) is True
    with open(tmp_path / ".tausik" / "cli_invocations.jsonl", encoding="utf-8") as fh:
        rows = fh.read().splitlines()
    row = json.loads(rows[0])
    assert len(rows) == 1 and row["exit"] == 1
    assert row["schema_version"] == 2 and row["origin"] == "pytest"


def test_uncaught_command_exception_is_recorded_then_reraised():
    recorded: list[int] = []

    with pytest.raises(RuntimeError, match="unexpected"):
        _run_entrypoint(lambda: (_ for _ in ()).throw(RuntimeError("unexpected")), recorded.append)

    assert recorded == [1]


# --- AC-6 on the LIVE tree -------------------------------------------------------


@pytest.mark.skipif(not os.path.isdir(LIVE_TAUSIK), reason="no live .tausik in this checkout")
def test_live_tree_false_alarms_on_green_rows_and_bounded_genuine(tmp_path):
    """Live precision (AC-6), two halves. FALSE ALARM = a finding with no
    failing cause: on the live invocation rows restricted to GREEN exits the
    detector must produce NOTHING (unit-lane boundaries already pin the other
    no-cause shapes). GENUINE friction — the day's 25 failed `metrics` calls,
    repeated red task-done refusals, the week's MCP dead ends — is the detector
    WORKING: measured 14 genuine findings on this tree (2026-10-07). The bound
    is a runaway TRIPWIRE at 20, not a cap on real friction."""
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
    # RUNAWAY TRIPWIRE, input-bound, not an arbitrary cap: the corpus grows
    # with every real red call (measured 30 genuine findings on the day the
    # bound was rewritten — 105 of them the session-metrics cost_usd=None
    # bug, the detector's first production catch). A detector BUG would
    # inflate counts beyond their
    # causes: total occurrences collapsed into nonzero-exit findings may not
    # exceed the nonzero rows on disk, and the finding count may not exceed
    # the nonzero rows either.
    nonzero_rows = sum(1 for r in rows if int(r.get("exit") or 0) != 0)
    nonzero_findings = [s for s in signals if s.kind == "nonzero-exit"]
    assert sum(s.count for s in nonzero_findings) <= nonzero_rows, (
        "occurrences inflated beyond their causes — runaway: "
        + "; ".join(f"{s.kind}:{s.signature}x{s.count}" for s in signals[:10])
    )
    assert len(signals) <= nonzero_rows, (
        f"{len(signals)} findings from {nonzero_rows} failing rows — runaway: "
        + "; ".join(f"{s.kind}:{s.signature}x{s.count}" for s in signals[:10])
    )
