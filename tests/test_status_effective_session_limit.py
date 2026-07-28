"""session-extend-is-a-no-op-for-every-reader — status shows the limit it is held to.

`tausik session extend` records its new limit as an event, and the Rule 9.2
warning already resolved it that way. The DISPLAY did not: both the text line
and the compact JSON printed the configured base, so a user who extended to 300
kept reading "61m / 180m" and concluded the extension had not worked — while the
threshold that actually fires used 300.

Three readers, two formulas. The compact JSON read `data["session_max_minutes"]`
and the text renderer read `view["max_min"]`, and BOTH were the raw config
value; only the warning resolved the effective one. Fixing just the one that was
noticed would have moved the contradiction instead of ending it, so these pin
all three together.

`tausik doctor` deliberately keeps showing the base — it reports configuration,
not the state of an open session — and that intent is pinned here too, so the
next person does not "fix" the divergence back into a bug.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import status_view  # noqa: E402
from service_session_metrics import (  # noqa: E402
    effective_session_limit,
    session_overrun_warning,
)

_BASE = 180


class _FakeBackend:
    """Backend with a session and a controllable list of extend events."""

    def __init__(self, extends: list[int], active_minutes: int = 0):
        self._extends = extends
        self._active = active_minutes
        self.events_list_calls = 0
        self.capacity_called_with: list[int] = []

    def session_current(self):
        return {"id": 148, "started_at": "2026-07-28T07:42:35Z"}

    # `compute_active_minutes` drives the gap-based active clock off these two.
    # Empty results mean "no recorded activity", which keeps active time at 0 and
    # leaves these tests about the LIMIT rather than about the clock.
    def _q(self, *args, **kwargs):
        return []

    def _q1(self, *args, **kwargs):
        return None

    def events_list(self, entity_type=None, entity_id=None, n=None):
        self.events_list_calls += 1
        return [
            {
                "entity_type": "session",
                "entity_id": "148",
                "action": "session_extend",
                "details": f'{{"old_limit":{_BASE},"new_limit":{new},"active":0}}',
            }
            for new in self._extends
        ]

    def session_capacity_summary(self, cap):
        """Records the cap it is handed — an extension of TIME must not widen it."""
        self.capacity_called_with.append(cap)
        return {"used": 0, "cap": cap, "remaining": cap, "planned": 0}


class _FakeService:
    def __init__(self, be, active_minutes=0):
        self.be = be
        self._active = active_minutes

    def get_status(self):
        return {"session": {"id": 148}, "tasks_done": 1, "tasks_total": 2}

    def session_check_duration(self, max_minutes=None, *, effective_limit=None):
        return session_overrun_warning(self.be, max_minutes, effective_limit=effective_limit)

    def session_active_seconds(self):
        return self._active * 60

    def session_active_minutes(self):
        return self._active

    def session_wall_minutes(self):
        return self._active


def _build(monkeypatch, extends, active_minutes=0, include_rich=False):
    """Build a status view with config pinned to the base limit."""
    import project_config

    monkeypatch.setattr(
        project_config,
        "load_config",
        lambda *a, **k: {"session_max_minutes": _BASE, "session_capacity_calls": 200},
    )
    be = _FakeBackend(extends, active_minutes)
    svc = _FakeService(be, active_minutes)
    return status_view.build_status_view(svc, include_rich=include_rich)


def test_without_an_extension_nothing_changes(monkeypatch):
    view = _build(monkeypatch, extends=[])
    assert view["max_min"] == _BASE
    assert view["data"]["session_max_minutes"] == _BASE


def test_text_renderer_shows_the_extended_limit(monkeypatch):
    view = _build(monkeypatch, extends=[300], active_minutes=64)
    assert view["max_min"] == 300


def test_compact_json_carries_the_extended_limit(monkeypatch):
    """/start and tausik_session_open read this one — it must not lag the text line."""
    view = _build(monkeypatch, extends=[300], active_minutes=64)
    assert view["data"]["session_max_minutes"] == 300


def test_both_channels_agree(monkeypatch):
    """The defect was that these two disagreed with a third reader, not that one was wrong."""
    view = _build(monkeypatch, extends=[300], active_minutes=64)
    assert view["max_min"] == view["data"]["session_max_minutes"]


def test_successive_extensions_accumulate(monkeypatch):
    view = _build(monkeypatch, extends=[240, 300], active_minutes=10)
    assert view["max_min"] == 300


def test_warning_fires_without_an_extension_and_goes_quiet_with_one(monkeypatch):
    """AC2 — the warning was ALREADY correct; pin that the display fix did not break it.

    Same active time (200 min) on both sides: over the 180 base, under the 300 it
    was extended to. The warning must distinguish them.
    """
    import service_session_metrics

    monkeypatch.setattr(service_session_metrics, "session_active_minutes", lambda *a, **k: 200)

    assert session_overrun_warning(_FakeBackend([]), _BASE), "200 > 180 base — must warn"
    assert session_overrun_warning(_FakeBackend([300]), _BASE) is None, (
        "200 < 300 extended limit — warning must respect the extension"
    )
    assert effective_session_limit(_FakeBackend([300]), 148, _BASE) == 300
    assert effective_session_limit(_FakeBackend([]), 148, _BASE) == _BASE


def test_capacity_is_not_extended(monkeypatch):
    """NEGATIVE: extending TIME must not widen the call-capacity limit.

    Asserted on the value capacity is actually computed from, and compared
    BETWEEN a session with an extension and one without. An earlier version of
    this test checked for a key `build_status_view` never writes on any path, so
    it held whether the fix was present, reverted or broken — a claim, not a
    check. Two states that must produce the same capacity is a check.
    """
    import project_config

    monkeypatch.setattr(
        project_config,
        "load_config",
        lambda *a, **k: {"session_max_minutes": _BASE, "session_capacity_calls": 200},
    )

    caps = []
    for extends in ([], [300]):
        be = _FakeBackend(extends, 64)
        svc = _FakeService(be, 64)
        status_view.build_status_view(svc, include_rich=True)
        caps.append(be.capacity_called_with)

    assert caps[0] == caps[1] == [200], (
        f"capacity must come from config regardless of time extensions, got {caps}"
    )


def test_effective_limit_is_resolved_once_per_view(monkeypatch):
    """The limit and the Rule 9.2 warning must share ONE events scan.

    `build_status_view` renders the limit and asks for the overrun warning in the
    same pass, and both need the effective limit. Resolving it twice means a
    second `events_list` scan on the compact path behind `/start` — measured
    here rather than asserted by reading the code, so the duplicate cannot creep
    back in unnoticed.
    """
    import project_config

    monkeypatch.setattr(
        project_config,
        "load_config",
        lambda *a, **k: {"session_max_minutes": _BASE, "session_capacity_calls": 200},
    )
    be = _FakeBackend([300], 64)
    svc = _FakeService(be, 64)

    status_view.build_status_view(svc, include_rich=False)

    assert be.events_list_calls == 1, (
        f"session events scanned {be.events_list_calls}x for one view — the limit "
        "should be resolved once and handed to the warning"
    )

    # And the delta this measures is real, not incidental: asking for the warning
    # WITHOUT handing it the resolved limit costs exactly the extra scan the
    # assertion above forbids. That is what the pre-fix code did.
    session_overrun_warning(be, _BASE)
    assert be.events_list_calls == 2


def test_doctor_reports_the_configured_base_on_purpose():
    """Doctor describes CONFIGURATION; folding a session's extension in would lie."""
    src = open(
        os.path.join(os.path.dirname(__file__), "..", "scripts", "project_cli_doctor.py"),
        encoding="utf-8",
    ).read()
    assert "DELIBERATELY the configured base" in src, (
        "the intended divergence must stay documented, or it reads as the same bug"
    )
    assert "effective_session_limit" not in src


@pytest.mark.parametrize("bad", ["{not json", "", "{}"])
def test_unparsable_extend_event_falls_back_to_base(bad):
    """A corrupt event must not crash status or invent a limit."""

    class _Corrupt(_FakeBackend):
        def events_list(self, entity_type=None, entity_id=None, n=None):
            return [{"action": "session_extend", "details": bad}]

    assert effective_session_limit(_Corrupt([]), 148, _BASE) == _BASE
