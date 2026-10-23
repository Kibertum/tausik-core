"""Doctor must distinguish a zero-minute live session from no session."""

from __future__ import annotations

from project_cli_doctor import session_status_detail


class _Svc:
    def __init__(self, current: dict | None) -> None:
        self.current = current

    def session_current(self) -> dict | None:
        return self.current

    def session_active_minutes(self) -> int:
        return 0

    def session_wall_minutes(self) -> int:
        return 0


def test_newly_opened_zero_minute_session_is_active() -> None:
    assert session_status_detail(_Svc({"id": 7})) == "0m active / 0m wall"


def test_no_open_session_is_reported_as_absent() -> None:
    assert session_status_detail(_Svc(None)) == "no active session"
