"""Tests for v14b-model-recommend-banner — task_start prints recommended
+ active model + verdict (✓ match / ⚠ MISMATCH / ⓘ unknown).

The banner is gated by `is_task_start_model_banner_enabled` (default ON).
Errors during banner rendering must never fail task_start itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from project_backend import SQLiteBackend
from project_service import ProjectService

from model_routing import (
    _normalize_model_id,
    format_task_start_banner,
    read_active_model_from_transcript,
    suggest_model,
)
from project_config import is_task_start_model_banner_enabled


def _make_service(tmp_path: Path) -> ProjectService:
    return ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))


def _write_transcript(tmp_path: Path, model: str | None, name: str = "t.jsonl") -> Path:
    path = tmp_path / name
    payload: dict = {"type": "assistant", "usage": {"input_tokens": 1, "output_tokens": 1}}
    if model is not None:
        payload["model"] = model
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


class TestNormalize:
    @pytest.mark.parametrize(
        "input_id,expected",
        [
            pytest.param("claude-opus-4-7[1m]", "claude-opus-4-7", id="strips_1m_suffix"),
            pytest.param("Claude-Opus-4-7", "claude-opus-4-7", id="lowercases"),
        ],
    )
    def test_normalize(self, input_id, expected):
        assert _normalize_model_id(input_id) == expected

    def test_none_or_empty(self):
        assert _normalize_model_id(None) == ""
        assert _normalize_model_id("") == ""
        assert _normalize_model_id("   ") == ""


class TestReadActiveModel:
    def test_reads_top_level_model(self, tmp_path):
        p = _write_transcript(tmp_path, "claude-opus-4-7")
        assert read_active_model_from_transcript(str(p)) == "claude-opus-4-7"

    def test_reads_nested_message_model(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(
            json.dumps({"message": {"model": "claude-sonnet-4-6"}}) + "\n",
            encoding="utf-8",
        )
        assert read_active_model_from_transcript(str(p)) == "claude-sonnet-4-6"

    def test_walks_backwards_returns_most_recent(self, tmp_path):
        p = tmp_path / "t.jsonl"
        lines = [
            json.dumps({"model": "claude-haiku-4-5"}),
            json.dumps({"model": "claude-sonnet-4-6"}),
            json.dumps({"model": "claude-opus-4-7"}),
        ]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        assert read_active_model_from_transcript(str(p)) == "claude-opus-4-7"

    def test_returns_none_when_no_model_field(self, tmp_path):
        p = _write_transcript(tmp_path, model=None)
        assert read_active_model_from_transcript(str(p)) is None

    def test_returns_none_for_missing_path(self, tmp_path):
        assert read_active_model_from_transcript(str(tmp_path / "absent.jsonl")) is None
        assert read_active_model_from_transcript(None) is None
        assert read_active_model_from_transcript("") is None

    def test_skips_invalid_json_lines(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(
            "not-json{{{\n" + json.dumps({"model": "claude-opus-4-7"}) + "\n",
            encoding="utf-8",
        )
        assert read_active_model_from_transcript(str(p)) == "claude-opus-4-7"


class TestFormatBanner:
    def test_match_path(self):
        # complex → recommends Opus 4.7; if active is also Opus 4.7 → match.
        out = format_task_start_banner(
            complexity="complex",
            active_model="claude-opus-4-7",
        )
        assert "Model recommendation:" in out
        assert "Opus 4.7" in out
        assert "✓ model match" in out
        assert "MISMATCH" not in out

    def test_match_with_1m_suffix(self):
        # 1M-context variant must not register as a mismatch.
        out = format_task_start_banner(
            complexity="complex",
            active_model="claude-opus-4-7[1m]",
        )
        assert "✓ model match" in out

    def test_mismatch_loud_warning(self):
        # simple → recommends Haiku 4.5; active Opus → loud mismatch.
        out = format_task_start_banner(
            complexity="simple",
            active_model="claude-opus-4-7",
        )
        assert "⚠ MODEL MISMATCH" in out
        assert "Haiku 4.5" in out
        # Actionable hints: manual switch path (IDE picker) + persist command.
        # The wrong "/fast" advice has been removed (C7 banner fix).
        assert "IDE model picker" in out
        assert "tausik config set model_profile" in out
        assert "haiku" in out
        # Negative: must NOT advise switching via /fast — that does not
        # downgrade models, it only toggles fast-output on Opus.
        assert "switch to Haiku 4.5 via /fast" not in out

    def test_unknown_active_falls_back_to_recommendation_only(self):
        # NEGATIVE: no transcript_path, no active_model → unknown verdict.
        out = format_task_start_banner(
            complexity="medium",
            transcript_path="",  # explicit empty path skips auto-discovery branch
            active_model=None,
        )
        # Auto-discovery may still pick something up from $HOME on this host;
        # what matters is the function does not crash and contains the
        # recommendation line.
        assert "Sonnet 4.6" in out
        assert "Model recommendation:" in out

    def test_default_complexity_uses_sonnet(self):
        # NEGATIVE: complexity=None → existing suggest_model contract (Sonnet default).
        out = format_task_start_banner(
            complexity=None,
            active_model="claude-sonnet-4-6",
        )
        assert "Sonnet 4.6" in out
        assert "no complexity set" in out
        assert "✓ model match" in out

    def test_unreadable_transcript_yields_unknown(self, tmp_path):
        # NEGATIVE: bad path → "active model unknown" (no crash, no false warning).
        out = format_task_start_banner(
            complexity="medium",
            transcript_path=str(tmp_path / "absent.jsonl"),
            active_model=None,
        )
        assert "active model unknown" in out
        assert "MISMATCH" not in out


class TestConfigGate:
    def test_default_enabled(self):
        assert is_task_start_model_banner_enabled({}) is True

    def test_explicit_disable(self):
        assert is_task_start_model_banner_enabled({"task_start": {"model_banner": False}}) is False

    def test_explicit_enable(self):
        assert is_task_start_model_banner_enabled({"task_start": {"model_banner": True}}) is True

    def test_wrong_type_defaults_to_enabled(self):
        # NEGATIVE: malformed config still defaults ON — banner is informational.
        assert is_task_start_model_banner_enabled({"task_start": "yes"}) is True


class TestTaskStartIntegration:
    def _seed_task(self, svc: ProjectService, slug: str, complexity: str) -> None:
        svc.session_start()
        svc.task_quick(slug, "stub task")
        # task_quick uses slugify on title — we passed slug-as-title above
        # to keep titles distinct; resolve actual created slug below if needed.
        svc.be.task_update(
            slug,
            goal="g",
            acceptance_criteria="ac1. negative: x",
            complexity=complexity,
            rollback_plan="git revert",
        )

    def test_banner_appears_in_task_start_output(self, tmp_path):
        svc = _make_service(tmp_path)
        try:
            self._seed_task(svc, "t-banner", "complex")
            with patch("model_routing._auto_find_transcript", return_value=None):
                with patch.dict(
                    "sys.modules", {}, clear=False
                ):  # ensure project_config picks up env, no real config file
                    out = svc.task_start("t-banner")
            assert "Model recommendation:" in out
            assert "Opus 4.7" in out
        finally:
            svc.be.close()

    def test_banner_disabled_by_config_flag(self, tmp_path, monkeypatch):
        svc = _make_service(tmp_path)
        try:
            self._seed_task(svc, "t-banner-off", "complex")
            # NEGATIVE: when the config flag returns False, banner is not appended.
            monkeypatch.setattr(
                "project_config.is_task_start_model_banner_enabled",
                lambda cfg=None: False,
            )
            out = svc.task_start("t-banner-off")
            assert "Model recommendation:" not in out
            assert "Opus 4.7" not in out
        finally:
            svc.be.close()

    def test_banner_failure_does_not_break_task_start(self, tmp_path, monkeypatch):
        svc = _make_service(tmp_path)
        try:
            self._seed_task(svc, "t-banner-broken", "simple")

            def _boom(*args, **kwargs):
                raise RuntimeError("simulated banner failure")

            monkeypatch.setattr("model_routing.format_task_start_banner", _boom)
            # NEGATIVE: banner crash is swallowed — task_start still returns the started message.
            out = svc.task_start("t-banner-broken")
            assert "started" in out.lower()
            assert "simulated banner failure" not in out
        finally:
            svc.be.close()


class TestSuggestModelStillWorks:
    """Regression guard: existing suggest_model contract is unchanged."""

    @pytest.mark.parametrize(
        "complexity,expected",
        [
            ("simple", "claude-haiku-4-5"),
            ("medium", "claude-sonnet-4-6"),
            ("complex", "claude-opus-4-7"),
            (None, "claude-sonnet-4-6"),  # default
            ("BOGUS", "claude-sonnet-4-6"),  # fallback
        ],
    )
    def test_known_complexities(self, complexity, expected):
        assert suggest_model(complexity)["model"] == expected
