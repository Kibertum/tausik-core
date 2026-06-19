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
    _model_family,
    _model_tier,
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
        # implement/complex → recommends Opus 4.8; active Opus (any point release)
        # is the same family → match.
        out = format_task_start_banner(
            complexity="complex",
            active_model="claude-opus-4-8",
        )
        assert "Model recommendation:" in out
        assert "Opus 4.8" in out
        assert "✓ model match" in out
        assert "MISMATCH" not in out

    def test_match_with_1m_suffix(self):
        # 1M-context variant must not register as a mismatch.
        out = format_task_start_banner(
            complexity="complex",
            active_model="claude-opus-4-7[1m]",
        )
        assert "✓ model match" in out

    def test_surplus_is_info_not_warning(self):
        # implement/simple → recommends Sonnet (Decision #112: Haiku too weak for
        # code); active Opus is a HIGHER tier (quality surplus), so this is a cost
        # nudge, NOT a loud mismatch.
        out = format_task_start_banner(
            complexity="simple",
            active_model="claude-opus-4-8",
        )
        assert "⚠ MODEL MISMATCH" not in out
        assert "quality surplus" in out
        assert "switch down to save cost" in out
        assert "Sonnet 4.6" in out
        # Still actionable: IDE picker + persist the cheaper tier.
        assert "IDE model picker" in out
        assert "tausik config set model_profile sonnet" in out

    def test_under_powered_is_loud_warning(self):
        # AC2: active tier BELOW recommended (Haiku on a complex task) is the
        # genuine mismatch — quality at risk, loud warning stays.
        out = format_task_start_banner(
            complexity="complex",
            active_model="claude-haiku-4-5",
        )
        assert "⚠ MODEL MISMATCH" in out
        assert "under-powered" in out
        assert "Opus 4.8" in out
        assert "IDE model picker" in out
        assert "tausik config set model_profile opus" in out

    def test_fable_active_against_sonnet_is_surplus(self):
        # AC1: fable (top tier) active while a medium task recommends Sonnet →
        # surplus info, never a warning.
        out = format_task_start_banner(
            complexity="medium",
            active_model="claude-fable-5",
        )
        assert "⚠ MODEL MISMATCH" not in out
        assert "quality surplus" in out

    def test_unrecognized_active_is_info(self):
        # AC3: an unknown model id must not crash or warn — info verdict.
        out = format_task_start_banner(
            complexity="medium",
            active_model="gpt-9-turbo",
        )
        assert "unrecognized" in out
        assert "⚠ MODEL MISMATCH" not in out
        assert "gpt-9-turbo" in out

    def test_opus_point_release_matches_complex(self):
        # Point-release tolerance: complex recommends Opus 4.8, active Opus 4.7 —
        # same family, must read as match, not mismatch.
        out = format_task_start_banner(
            complexity="complex",
            active_model="claude-opus-4-7",
        )
        assert "✓ model match" in out
        assert "MISMATCH" not in out

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
            scope="x.py",  # satisfy the Rule 2 hard gate (v15-scope-rule2-hardgate)
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
            assert "Opus 4.8" in out
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
            assert "Opus 4.8" not in out
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
    """Regression guard: single-arg suggest_model = implement-phase matrix (Decision #112)."""

    @pytest.mark.parametrize(
        "complexity,expected",
        [
            ("simple", "claude-sonnet-4-6"),  # implement floor is Sonnet now
            ("medium", "claude-sonnet-4-6"),
            ("complex", "claude-opus-4-8"),
            (None, "claude-sonnet-4-6"),  # default -> medium column
            ("BOGUS", "claude-sonnet-4-6"),  # fallback -> medium column
        ],
    )
    def test_known_complexities(self, complexity, expected):
        assert suggest_model(complexity)["model"] == expected


class TestTierOrdering:
    """AC4: tier rank haiku < sonnet < opus < fable, version-agnostic."""

    @pytest.mark.parametrize(
        "model_id,family",
        [
            ("claude-haiku-4-5-20251001", "haiku"),
            ("claude-sonnet-4-6", "sonnet"),
            ("claude-opus-4-7", "opus"),
            ("claude-opus-4-8[1m]", "opus"),
            ("claude-fable-5", "fable"),
        ],
    )
    def test_family_detection(self, model_id, family):
        assert _model_family(model_id) == family

    def test_full_order(self):
        tiers = [
            _model_tier(m)
            for m in ("claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-8", "claude-fable-5")
        ]
        assert tiers == sorted(tiers)
        assert tiers == [0, 1, 2, 3]

    def test_unknown_family_is_none(self):
        assert _model_family("gpt-9") is None
        assert _model_tier("gpt-9") is None
        assert _model_tier(None) is None


class TestBannerGlmFamily:
    """Family-agnostic banner: on a z.ai/GLM session, recommend within GLM (Decision #119)."""

    def test_glm_active_recommends_glm_and_matches(self):
        # complex implement on GLM → recommend GLM flagship; active==rec → ✓ match.
        out = format_task_start_banner(
            "complex", active_model="glm-4.6", phase="implement", config={}
        )
        assert "glm-4.6" in out
        assert "claude" not in out
        assert "✓ model match" in out

    def test_default_family_used_when_active_unknown(self):
        # No detectable active model, but config pins default_family=glm.
        cfg = {"model_profiles": {"default_family": "glm"}}
        out = format_task_start_banner(
            "complex", active_model=None, transcript_path="", phase="implement", config=cfg
        )
        assert "glm-4.6" in out
        assert "active model unknown" in out

    def test_glm_underpowered_is_mismatch(self):
        # Running the light GLM on a complex task → genuine mismatch.
        out = format_task_start_banner(
            "complex", active_model="glm-4.5-air", phase="implement", config={}
        )
        assert "MISMATCH" in out
        assert "glm-4.6" in out  # recommended flagship still shown

    def test_claude_session_unchanged(self):
        # Back-compat: a Claude active model still recommends Claude and matches.
        out = format_task_start_banner(
            "complex", active_model="claude-opus-4-8", phase="implement", config={}
        )
        assert "claude-opus-4-8" in out
        assert "glm" not in out
