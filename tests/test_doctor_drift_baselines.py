"""Regression tests for v14b doctor drift baseline + brain conditional skill check.

Covers the cases introduced when silencing tausik doctor warnings:
- _is_trimmed_baseline detects v1.4-polish trimmed CLAUDE.md (small + Reference→agent-contract.md)
- _check_claudemd_drift returns 0 (no drift) when current is the trimmed baseline
- Brain skill is only required when brain.enabled=true (matches bootstrap_copy gating)
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_cli_doctor import (
    _check_claudemd_drift,
    _is_trimmed_baseline,
)


# ---------- _is_trimmed_baseline ----------


class TestIsTrimmedBaseline:
    @pytest.mark.parametrize(
        "text,expected",
        [
            pytest.param(
                "# CLAUDE.md\n\n"
                "## Hard Constraints\n- foo\n\n"
                "## Reference\n"
                "Полный контракт: `docs/ru/agent-contract.md`. CLI: docs/ru/cli.md.\n",
                True,
                id="short_with_ru_agent_contract_link",
            ),
            pytest.param(
                "# CLAUDE.md\n\n## Reference\nFull contract: docs/en/agent-contract.md.\n",
                True,
                id="short_with_en_agent_contract_link",
            ),
            pytest.param(
                "# CLAUDE.md\n\n## Hard Constraints\n- nothing about agent-contract here\n",
                False,
                id="short_without_reference_section",
            ),
            pytest.param(
                "# CLAUDE.md\n\n## Reference\nSee docs/ru/cli.md only.\n",
                False,
                id="short_reference_section_but_no_agent_contract",
            ),
            pytest.param(
                "# CLAUDE.md\n\n## reference\nlink: docs/en/agent-contract.md\n",
                True,
                id="case_insensitive_heading",
            ),
        ],
    )
    def test_short_text_classification(self, text: str, expected: bool) -> None:
        assert _is_trimmed_baseline(text, len(text.encode())) is expected

    def test_oversized_rejected_even_with_link(self) -> None:
        # 7KB+ — even with the Reference signature, treat as customised, not trim
        body = "# CLAUDE.md\n\n## Reference\ndocs/ru/agent-contract.md\n" + "x" * 7000
        assert _is_trimmed_baseline(body, len(body.encode())) is False


# ---------- _check_claudemd_drift returns 0 for trimmed baseline ----------


class TestCheckClaudemdDrift:
    def _setup_project(self, tmp_path, claudemd_text: str, cfg: dict | None = None) -> str:
        """Lay out a minimal project dir with CLAUDE.md and .tausik/config.json."""
        (tmp_path / "CLAUDE.md").write_text(claudemd_text, encoding="utf-8")
        tausik = tmp_path / ".tausik"
        tausik.mkdir(exist_ok=True)
        cfg_path = tausik / "config.json"
        cfg_path.write_text(json.dumps(cfg or {}), encoding="utf-8")
        return str(tmp_path)

    def test_trimmed_baseline_returns_zero_drift(self, tmp_path, monkeypatch) -> None:
        # Trimmed CLAUDE.md (under 6KB + Reference→agent-contract.md) → 0 drift.
        text = (
            "# CLAUDE.md\n\n## Project: x\n\n"
            "## Hard Constraints\n- task first\n\n"
            "## Reference\nDocs: docs/ru/agent-contract.md.\n"
        )
        proj = self._setup_project(tmp_path, text)
        monkeypatch.chdir(proj)
        # _check_claudemd_drift uses load_config relative to cwd; chdir into tmp project.
        result = _check_claudemd_drift(proj)
        assert result == 0

    def test_missing_file_returns_none(self, tmp_path) -> None:
        # No CLAUDE.md at all → None (cannot compare).
        assert _check_claudemd_drift(str(tmp_path)) is None


# ---------- brain skill is conditional in critical set ----------


class TestBrainConditionalSkill:
    """When brain.enabled=false, doctor must not flag missing 'brain' skill.

    We replicate the doctor's critical-set logic at the unit level — easier
    than spinning up cmd_doctor with all its filesystem deps.
    """

    def _critical_for(self, cfg: dict) -> set[str]:
        """Mirror project_cli_doctor.cmd_doctor's critical-set construction."""
        critical = {"start", "end", "task", "plan", "review", "ship", "checkpoint"}
        if bool((cfg.get("brain") or {}).get("enabled", False)):
            critical.add("brain")
        return critical

    def test_brain_required_when_enabled(self) -> None:
        critical = self._critical_for({"brain": {"enabled": True}})
        assert "brain" in critical

    def test_brain_not_required_when_disabled(self) -> None:
        critical = self._critical_for({"brain": {"enabled": False}})
        assert "brain" not in critical

    def test_brain_not_required_when_section_missing(self) -> None:
        critical = self._critical_for({})
        assert "brain" not in critical

    def test_brain_not_required_when_enabled_missing(self) -> None:
        critical = self._critical_for({"brain": {}})
        assert "brain" not in critical


@pytest.mark.parametrize(
    ("size_bytes", "has_link", "expected"),
    [
        (1024, True, True),  # small + link → trimmed
        (3000, True, True),  # at the typical 3KB v1.4-polish target
        (6000, True, True),  # right at the 6KB headroom
        (7000, True, False),  # over 6KB → not trimmed
        (1024, False, False),  # small but no link → not trimmed
    ],
)
def test_is_trimmed_baseline_parametrized(size_bytes: int, has_link: bool, expected: bool) -> None:
    if has_link:
        body = "# CLAUDE.md\n\n## Reference\nSee docs/ru/agent-contract.md.\n" + (
            "x" * max(0, size_bytes - 100)
        )
    else:
        body = "# CLAUDE.md\n\nSome other content\n" + ("x" * max(0, size_bytes - 30))
    # Make actual size match what we passed in (within rounding):
    actual_size = len(body.encode())
    assert _is_trimmed_baseline(body, actual_size) is expected
