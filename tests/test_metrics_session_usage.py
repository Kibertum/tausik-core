from __future__ import annotations

from pathlib import Path

from project_backend import SQLiteBackend
from project_parser import build_parser
from project_service import ProjectService


def _make_service(tmp_path: Path) -> ProjectService:
    db_path = tmp_path / "tausik.db"
    be = SQLiteBackend(str(db_path))
    return ProjectService(be)


def test_metrics_record_session_persists_usage(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        msg = svc.metrics_record_session(
            tokens_input=1000,
            tokens_output=250,
            tokens_total=1250,
            cost_usd=0.0125,
            tool_calls=3,
            model="claude-sonnet-4-6",
        )
        assert "Session usage recorded" in msg

        m = svc.get_metrics()
        usage = m.get("session_usage") or {}
        assert usage["sessions_with_usage"] == 1
        assert usage["tokens_input"] == 1000
        assert usage["tokens_output"] == 250
        assert usage["tokens_total"] == 1250
        assert usage["cost_usd"] == 0.0125
        last = usage.get("last_session") or {}
        assert last.get("model") == "claude-sonnet-4-6"
    finally:
        svc.be.close()


def test_metrics_record_session_cli_args_are_supported() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "metrics",
            "record-session",
            "--tokens-input",
            "10",
            "--tokens-output",
            "5",
            "--tokens-total",
            "15",
            "--cost-usd",
            "0.0003",
            "--tool-calls",
            "2",
            "--model",
            "claude-haiku-4-5",
        ]
    )
    assert args.command == "metrics"
    assert args.metrics_cmd == "record-session"
    assert args.tokens_total == 15
    assert args.model == "claude-haiku-4-5"

