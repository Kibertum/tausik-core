"""v15mr-subagent-model-hints: phase->model hints for Agent-tool subagents."""

from __future__ import annotations

import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


# --- AC1: skills with Agent calls document the per-phase subagent model -------


class TestSkillHints:
    def test_review_documents_reviewer_models(self):
        text = _read("harness", "skills", "review", "SKILL.md")
        assert "Subagent model (phase=code-review)" in text
        assert 'model="sonnet"' in text
        # critic / synthesis escalates to the stronger reasoner
        assert "Opus 4.8" in text

    def test_ship_documents_sonnet_subagents(self):
        text = _read("harness", "skills", "ship", "SKILL.md")
        assert "Subagent model (phase=code-review)" in text
        assert 'model: "sonnet"' in text

    def test_debug_documents_gatefixer_model(self):
        text = _read("harness", "skills", "debug", "SKILL.md")
        assert "Subagent model (phase=code-review)" in text
        assert 'model="sonnet"' in text


# --- AC2: a guide page maps phase -> subagent model --------------------------


class TestGuidePage:
    def test_matrix_doc_has_subagent_section(self):
        text = _read("docs", "ru", "research", "model-routing-matrix.md")
        assert "Сабагенты (Agent-tool)" in text
        # all three phase rows present
        assert "Haiku 4.5" in text  # search / exploration
        assert "Sonnet 4.6" in text  # code-review / verification
        assert "Opus 4.8" in text  # reasoning / synthesis


# --- AC3: missing model= is NOT an error — the hint is advisory ---------------


class TestAdvisoryNotMandatory:
    def test_guide_states_hint_is_optional(self):
        text = _read("docs", "ru", "research", "model-routing-matrix.md")
        # The doc must explicitly frame model= as a hint, not a requirement, so a
        # legacy Agent() call without model= is valid and never fails a drift check.
        assert "подсказка, не требование" in text

    def test_legacy_subagent_call_without_model_is_allowed(self):
        # `end` references a subagent inline without a model= hint. The drift
        # check keys on the guidance marker, NOT on model= in every Agent call,
        # so this legacy skill must pass without carrying the hint.
        text = _read("harness", "skills", "end", "SKILL.md")
        assert "subagent" in text.lower()
        assert "Subagent model (phase=" not in text  # not required to carry it
