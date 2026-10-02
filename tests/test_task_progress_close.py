"""Compound progress/close replays the existing service operations in order."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import crypto_keys
from project_backend import SQLiteBackend
from project_service import ProjectService
from task_progress_close import run_progress_close

pytestmark = pytest.mark.verify_first


EVIDENCE = (
    "AC-1: ✓ exercised through real service operations. "
    "Domain: task state and durable verification evidence agree."
)

FROZEN_GREEN_REPLAY = {
    "original_returns": ["task_log", "task_step", "verification", "task_done"],
    "compound_returns": ["progress_close"],
}


def _project(root: Path, *, steps: int = 1) -> ProjectService:
    (root / ".tausik").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "scripts" / "feature.py").write_text("value = 1\n", encoding="utf-8")
    crypto_keys.init_keys(str(root))
    svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
    svc.task_add(None, "work", "Work", complexity="simple")
    svc.task_update(
        "work",
        goal="close deterministic work",
        acceptance_criteria="AC-1 state agrees. Negative: red verification refuses closure.",
        scope="scripts/feature.py",
        scope_exclude="other files",
        rollback_plan="revert test change",
        relevant_files=json.dumps(["scripts/feature.py"]),
    )
    svc.task_plan("work", [f"step {index}" for index in range(1, steps + 1)])
    svc.task_start("work")
    return svc


def _gate(passed: bool):
    result = {
        "name": "stub-behavior",
        "passed": passed,
        "severity": "block",
        "output": "ok" if passed else "boom",
    }
    return lambda *_args, **_kwargs: (passed, [result])


def _task_state(svc: ProjectService) -> tuple[str, list[dict], list[str]]:
    task = svc.task_show("work")
    plan = json.loads(task["plan"])
    messages = [row["message"] for row in svc.task_logs("work")]
    return task["status"], plan, messages


def _verify_exit_codes(svc: ProjectService) -> list[int]:
    return [int(row["exit_code"]) for row in svc.be.verification_runs_for_task("work")]


def test_green_replay_matches_four_real_operations_and_removes_three_boundaries(
    tmp_path, monkeypatch
):
    legacy_root = tmp_path / "legacy"
    compound_root = tmp_path / "compound"
    legacy = _project(legacy_root)
    compound = _project(compound_root)
    monkeypatch.setattr("gate_runner.run_gates", _gate(True))
    try:
        monkeypatch.chdir(legacy_root)
        original_returns = [
            legacy.task_log("work", "final progress"),
            legacy.task_step("work", 1),
        ]
        verified = legacy.run_verify_for_task("work", scope="manual", trigger="verify")
        original_returns.append(verified)
        original_returns.append(
            legacy.task_done(
                "work",
                ac_verified=True,
                no_knowledge=True,
                evidence=EVIDENCE,
                no_changelog=True,
                verify_handle=verified["verify_handle"],
            )
        )

        monkeypatch.chdir(compound_root)
        compound_returns = [
            run_progress_close(
                compound,
                "work",
                "final progress",
                1,
                close=True,
                verify=True,
                ac_verified=True,
                evidence=EVIDENCE,
                no_knowledge=True,
                no_changelog=True,
            )
        ]

        assert compound_returns[0]["ok"] is True
        assert compound_returns[0]["closed"] is True
        assert compound_returns[0]["completed"] == [
            "task_log",
            "task_step",
            "verification",
            "task_done",
        ]
        assert _task_state(compound) == _task_state(legacy)
        compound_codes = _verify_exit_codes(compound)
        assert compound_codes == _verify_exit_codes(legacy)
        assert compound_codes and set(compound_codes) == {0}
        assert len(original_returns) - len(compound_returns) == 3
        assert len(FROZEN_GREEN_REPLAY["original_returns"]) == len(original_returns)
    finally:
        legacy.be.close()
        compound.be.close()


def test_red_verify_preserves_same_partial_state_and_diagnostic_as_separate_calls(
    tmp_path, monkeypatch
):
    legacy_root = tmp_path / "legacy-red"
    compound_root = tmp_path / "compound-red"
    legacy = _project(legacy_root)
    compound = _project(compound_root)
    monkeypatch.setattr("gate_runner.run_gates", _gate(False))
    try:
        monkeypatch.chdir(legacy_root)
        legacy.task_log("work", "attempted close")
        legacy.task_step("work", 1)
        legacy.run_verify_for_task("work", scope="manual", trigger="verify")

        monkeypatch.chdir(compound_root)
        result = run_progress_close(
            compound,
            "work",
            "attempted close",
            1,
            close=True,
            verify=True,
            ac_verified=True,
            evidence=EVIDENCE,
        )

        assert result["ok"] is False and "closed" not in result, result
        assert result["failure"]["stage"] == "verification"
        projection = result["verification"]
        assert all("output" not in row for row in projection["results"])
        evidence_path = compound_root / projection["summary"][1].split(": ", 1)[1]
        assert "boom" in evidence_path.read_text(encoding="utf-8")
        assert any("stub-behavior" in line for line in projection["summary"])
        assert _task_state(compound) == _task_state(legacy)
        assert _verify_exit_codes(compound) == _verify_exit_codes(legacy) == [1]
    finally:
        legacy.be.close()
        compound.be.close()


@pytest.mark.parametrize("scenario", ["incomplete_plan", "missing_evidence", "stale_handle"])
def test_close_refusals_keep_task_open_with_no_success_flag(tmp_path, monkeypatch, scenario):
    root = tmp_path / scenario
    svc = _project(root, steps=2 if scenario == "incomplete_plan" else 1)
    monkeypatch.setattr("gate_runner.run_gates", _gate(True))
    try:
        monkeypatch.chdir(root)
        handle = None
        evidence = EVIDENCE
        if scenario == "missing_evidence":
            evidence = None
        if scenario == "stale_handle":
            verified = svc.run_verify_for_task("work", scope="manual", trigger="verify")
            handle = verified["verify_handle"]
            (root / "scripts" / "feature.py").write_text(
                "value = 2\n# changed after verify\n", encoding="utf-8"
            )

        result = run_progress_close(
            svc,
            "work",
            "final attempt",
            1,
            close=True,
            verify=scenario != "stale_handle",
            verify_handle=handle,
            ac_verified=True,
            evidence=evidence,
            no_knowledge=True,
            no_changelog=True,
        )

        assert result["ok"] is False and "closed" not in result, result
        assert result["failure"]["stage"] == "task_done"
        assert svc.task_show("work")["status"] == "active"
        expected = {
            "incomplete_plan": "Plan incomplete",
            "missing_evidence": "evidence",
            "stale_handle": "changed since",
        }
        assert expected[scenario].lower() in result["failure"]["message"].lower()
    finally:
        svc.be.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"step_num": True},
        {"step_num": 1, "verify": "yes"},
        {"step_num": 1, "verify": True, "verify_handle": "1." + "a" * 32},
    ],
)
def test_invalid_shape_is_refused_before_first_mutation(tmp_path, kwargs):
    svc = _project(tmp_path / "invalid")
    before = _task_state(svc)
    try:
        with pytest.raises(ValueError):
            run_progress_close(
                svc,
                "work",
                "must not be written",
                close=bool(kwargs.get("verify") or kwargs.get("verify_handle")),
                **kwargs,
            )
        assert _task_state(svc) == before
    finally:
        svc.be.close()


def test_mcp_unknown_compound_key_is_refused_before_mutation(tmp_path, monkeypatch):
    svc = _project(tmp_path / "mcp-invalid")
    before = _task_state(svc)
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "harness/claude/mcp/project"))
    from handlers_task import _do_task_done

    try:
        with pytest.raises(ValueError, match="only message, step and verify"):
            _do_task_done(
                svc,
                {
                    "slug": "work",
                    "compound": json.dumps(
                        {"message": "must not write", "step": 1, "verfiy": True}
                    ),
                },
            )
        assert _task_state(svc) == before
    finally:
        svc.be.close()


def test_cli_and_mcp_progress_wrappers_have_identical_durable_state(tmp_path, monkeypatch, capsys):
    cli = _project(tmp_path / "cli-progress")
    mcp = _project(tmp_path / "mcp-progress")
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "harness/claude/mcp/project"))
    from handlers_task import _do_task_step
    from project_cli_task import cmd_task
    from project_parser import build_parser

    try:
        cli_args = build_parser().parse_args(
            ["task", "step", "work", "1", "--message", "progress through wrapper"]
        )
        cmd_task(cli, cli_args)
        cli_result = json.loads(capsys.readouterr().out)
        mcp_result = json.loads(
            _do_task_step(
                mcp,
                {"slug": "work", "step_num": 1, "message": "progress through wrapper"},
            )
        )

        assert (
            cli_result["completed"]
            == mcp_result["completed"]
            == [
                "task_log",
                "task_step",
            ]
        )
        assert _task_state(cli) == _task_state(mcp)
    finally:
        cli.be.close()
        mcp.be.close()


def test_cli_compound_refusal_prints_diagnostic_and_exits_nonzero(tmp_path, monkeypatch, capsys):
    svc = _project(tmp_path / "cli-refusal", steps=2)
    monkeypatch.setattr("gate_runner.run_gates", _gate(True))
    from project_cli_task import cmd_task
    from project_parser import build_parser

    try:
        monkeypatch.chdir(tmp_path / "cli-refusal")
        args = build_parser().parse_args(
            [
                "task",
                "done",
                "work",
                "--message",
                "attempt close",
                "--step",
                "1",
                "--verify",
                "--ac-verified",
                "--evidence",
                EVIDENCE,
                "--no-knowledge",
                "--no-changelog",
            ]
        )
        with pytest.raises(SystemExit) as exc:
            cmd_task(svc, args)

        result = json.loads(capsys.readouterr().out)
        assert exc.value.code == 1
        assert result["ok"] is False and "closed" not in result
        assert result["failure"]["stage"] == "task_done"
        assert _task_state(svc)[1][0]["done"] is True
        assert svc.task_show("work")["status"] == "active"
    finally:
        svc.be.close()
