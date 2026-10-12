"""The doctor's Session-model check names its sources, not just its answers.

service_doctor_model_source docstring promised DECLARED means the check names
WHICH source answered — but until v73 the recorded row kept only the model id,
so the ok line could not keep that promise and the available-now line named
neither. These tests pin the contract on both ends: a recorded row names the
source stored at open time, a row recorded before sources existed says so
honestly instead of borrowing today's chain, and a silent host is handed the
way out without a model being guessed from its name.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import service_doctor_model_source as sdms  # noqa: E402


def _session(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {"id": 42, "model_id": None, "model_source": None}
    row.update(overrides)
    return row


class _Svc:
    def __init__(self, session: dict[str, object] | None):
        self._session = session

    class be:  # the attribute name the real service object exposes
        current: dict[str, object] | None = None

        @classmethod
        def session_current(cls) -> dict[str, object] | None:
            return cls.current


def _svc(session: dict[str, object] | None) -> _Svc:
    _Svc.be.current = session
    return _Svc(session)


def test_a_recorded_row_names_the_source_stored_at_open():
    rows = list(
        sdms.check_session_model(_svc(_session(model_id="glm-4.7", model_source="provider:kilo")))
    )
    severity, _, detail = rows[0]
    assert severity == "ok"
    assert "model=glm-4.7" in detail
    assert "declared by provider:kilo" in detail


def test_a_row_recorded_before_sources_stored_does_not_borrow_todays_chain(monkeypatch):
    """A legacy row's provenance is gone. Re-deriving today's chain and naming
    it would fabricate history — the same rule benchmark provenance follows."""

    def _wrong_answer() -> dict[str, str | None]:
        return {"model_id": "glm-4.6", "source": "provider:kilo", "model_version": None}

    monkeypatch.setattr(sdms, "resolve", _wrong_answer)
    rows = list(sdms.check_session_model(_svc(_session(model_id="glm-4.7", model_source=None))))
    severity, _, detail = rows[0]
    assert severity == "ok"
    assert "recorded before sources were stored" in detail
    assert "provider:kilo" not in detail, "today's chain must not be named as history"


def test_available_now_names_the_source_that_answers(monkeypatch):
    monkeypatch.setattr(
        sdms,
        "resolve",
        lambda: {"model_id": "glm-4.7", "source": "provider:kilo", "model_version": None},
    )
    rows = list(sdms.check_session_model(_svc(_session())))
    severity, _, detail = rows[0]
    assert severity == "warn"
    assert "provider:kilo" in detail
    assert "glm-4.7" in detail


@pytest.mark.parametrize("declared", [None, ""])
def test_silence_everywhere_stays_a_warning_and_names_the_way_out(monkeypatch, declared):
    """No source answers: the model is NOT inferred from the host's name, and
    the reader is handed the override variable instead of a grievance."""

    def _silence() -> dict[str, str | None]:
        return {"model_id": None, "source": declared, "model_version": None}

    monkeypatch.setattr(sdms, "resolve", _silence)
    rows = list(sdms.check_session_model(_svc(_session())))
    severity, _, detail = rows[0]
    assert severity == "warn"
    assert "TAUSIK_AGENT_MODEL" in detail
    assert "NOT guessed" in detail


def test_no_open_session_is_not_asked_and_not_complained_about():
    assert list(sdms.check_session_model(_svc(None))) == []
