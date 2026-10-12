"""Provider-aware worker routing keeps root switching honest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from model_route import route_work  # noqa: E402
from model_routing_adherence import aggregate_adherence, record_route_outcome  # noqa: E402
from providers.codex import CodexProvider, _model_from_tail  # noqa: E402


@pytest.mark.parametrize(
    ("name", "expected"),
    [("CODEX_THREAD_ID", "codex"), ("CODEX_SESSION_ID", "codex"), ("KILO_MODEL", "kilo")],
)
def test_host_detection_reaches_codex_and_kilo(name, expected, monkeypatch):
    from skill_profile_detect import _IDE_ENV_MARKERS, detect_ide

    for _host, marker in _IDE_ENV_MARKERS:
        monkeypatch.delenv(marker, raising=False)
    monkeypatch.setenv(name, "present")
    assert detect_ide() == expected


def test_codex_provider_reads_current_thread_model(tmp_path, monkeypatch):
    thread = "01-test-thread"
    journal = tmp_path / "sessions/2026/10/01" / f"rollout-{thread}.jsonl"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        "\n".join(
            [
                json.dumps({"type": "turn_context", "payload": {"model": "gpt-6-astra"}}),
                json.dumps({"type": "turn_context", "payload": {"model": "gpt-5.6-sol"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setenv("CODEX_THREAD_ID", thread)
    assert CodexProvider().get_active_model() == "gpt-5.6-sol"


def test_codex_tail_missing_or_malformed_is_unknown(tmp_path):
    missing = tmp_path / "missing.jsonl"
    assert _model_from_tail(missing) is None
    malformed = tmp_path / "bad.jsonl"
    malformed.write_text("not-json\n", encoding="utf-8")
    assert _model_from_tail(malformed) is None


def test_codex_complex_defaults_to_sol_medium_standard():
    route = route_work("complex", host="codex", active_model="gpt-5.6-sol", config={})
    assert route["model"] == "gpt-5.6-sol"
    assert route["reasoning_effort"] == "medium"
    assert route["speed_mode"] == "standard"
    assert route["capability"] == "spawn_subagent"
    assert route["applied"] is False
    assert route["root_session_switch"] == "unsupported"


def test_codex_simple_routes_down_and_high_risk_can_escalate():
    cheap = route_work("simple", host="codex", active_model="gpt-5.6-sol", config={})
    hard = route_work(
        "complex",
        phase="planning",
        risk="high",
        host="codex",
        active_model="gpt-5.6-sol",
        config={},
    )
    assert cheap["model"] == "gpt-5.6-terra"
    assert cheap["reasoning_effort"] == "medium"
    assert hard["model"] == "gpt-6-astra"
    assert hard["reasoning_effort"] == "high"


def test_bounded_medium_work_is_terra_regardless_of_phase():
    route = route_work(
        "simple",
        phase="planning",
        host="codex",
        active_model="gpt-5.6-sol",
        config={},
    )
    assert route["model"] == "gpt-5.6-terra"
    assert route["route_reason"] == "bounded simple/medium worker work defaults to Terra"


def test_kilo_keeps_glm_family_but_unverified_spawn_is_advisory():
    route = route_work("simple", host="kilo", active_model="glm-4.6", config={})
    assert route["family"] == "glm"
    assert route["model"].startswith("glm-")
    assert route["capability"] == "advisory"


def test_unknown_host_and_model_do_not_invent_application():
    route = route_work("simple", host="mystery", active_model="unknown-1", config={})
    assert route["capability"] == "advisory"
    assert route["applied"] is False


def test_unclassified_work_is_advisory_and_not_labeled_bounded():
    route = route_work(None, host="codex", active_model="gpt-5.6-sol", config={})
    assert route["capability"] == "advisory"
    assert route["eligible"] is False
    assert route["route_reason"] == "complexity is unclassified; no worker route selected"


def test_stale_openai_model_and_malformed_override_degrade_to_safe_defaults():
    route = route_work(
        "simple",
        host="codex",
        active_model="gpt-5.5-old",
        config={"model_profiles": {"families": {"openai": {"sonnet": {"model": ""}}}}},
    )
    assert route["family"] == "openai"
    assert route["model"] == "gpt-5.6-terra"
    assert route["applied"] is False


def test_unknown_risk_is_rejected():
    with pytest.raises(ValueError, match="Unknown risk"):
        route_work("simple", risk="maybe", config={})


def test_failed_quality_signal_escalates_one_tier_and_unknown_signal_is_rejected():
    route = route_work(
        "simple",
        quality_signal="verify_failed",
        host="codex",
        active_model="gpt-5.6-sol",
        config={},
    )
    assert route["model"] == "gpt-5.6-sol"
    assert route["reasoning_effort"] == "medium"
    assert route["quality_signal"] == "verify_failed"
    assert route["escalation_reason"] == "verify_failed"
    with pytest.raises(ValueError, match="Unknown quality signal"):
        route_work("simple", quality_signal="felt_hard", config={})


def test_astra_requires_separately_declared_high_risk():
    route = route_work(
        "simple",
        risk="high",
        host="codex",
        active_model="gpt-5.6-sol",
        config={},
    )
    assert route["model"] == "gpt-6-astra"
    assert route["route_reason"] == "high-risk work requires Astra"
    assert route["escalation_reason"] == "risk=high"


@pytest.mark.parametrize(
    "outcome", ["recommended", "selected", "applied", "rejected", "unavailable"]
)
def test_route_outcomes_are_explicit_and_do_not_pollute_legacy_fit(tmp_path, outcome):
    route = route_work("simple", host="codex", active_model="gpt-5.6-sol", config={})
    row = record_route_outcome(str(tmp_path), "route-1", route, outcome)
    assert row is not None
    assert row["schema_version"] == 2
    assert row["outcome"] == outcome
    assert row["model"] == "gpt-5.6-terra"
    assert row["host"] == "codex"
    assert row["route_reason"] == "bounded simple/medium worker work defaults to Terra"
    assert row["escalation_reason"] is None
    assert aggregate_adherence(str(tmp_path))["n"] == 0


def test_invalid_route_outcome_is_not_recorded(tmp_path):
    route = route_work("simple", host="codex", active_model="gpt-5.6-sol", config={})
    assert record_route_outcome(str(tmp_path), "route-1", route, "pretended") is None
    assert not (tmp_path / "routing_adherence.jsonl").exists()
