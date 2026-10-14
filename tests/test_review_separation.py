"""An L3 review record proves the one-family rule or is refused (github#157).

l3-dispatch-does-not-carry-the-author-model (1.10) made the record name both
models. 1.11.6 inverted the boundary: one model family per environment —
same-family review is the recordable form, and a reviewer from ANOTHER family
(a pulled Codex from a GLM host, Claude from Codex) is refused.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import external_reviewer as er
import review_separation as rs
from project_cli_review import cmd_review
from project_parser import build_parser


class _Be:
    def __init__(self):
        self.rows: list[dict] = []

    def review_record(self, **kw):
        self.rows.append(kw)
        return len(self.rows)


class _Svc:
    def __init__(self):
        self.be = _Be()

    def task_show(self, slug):
        return {"slug": slug}


def _record(svc, *extra):
    argv = ["review", "record", "--task", "t", *extra]
    cmd_review(svc, build_parser().parse_args(argv))


@pytest.fixture(autouse=True)
def _no_live_transcript(monkeypatch):
    # The author default reads the live transcript; tests must not see the host's.
    monkeypatch.setattr(rs, "resolve_author_model", lambda explicit: explicit)


@pytest.mark.parametrize(
    "extra, says",
    [
        (["--author-model", "claude-opus-5-5"], "--reviewer-model"),
        (["--reviewer-model", "claude-fable-5-1"], "--author-model"),
        (["--author-model", "claude-opus-5-5", "--reviewer-model", "gpt-x"], "not a recognised"),
        (
            ["--author-model", "glm-5.2", "--reviewer-model", "claude-opus-5-5"],
            "another model family",
        ),
        (
            ["--author-model", "claude-opus-5-5", "--reviewer-model", "glm-5.2"],
            "one model family per environment",
        ),
    ],
    ids=["no-reviewer", "unknown-author", "unknown-reviewer", "glm-claude", "claude-glm"],
)
def test_an_l3_that_pulls_another_family_or_hides_a_model_is_refused(extra, says, capsys):
    svc = _Svc()
    with pytest.raises(SystemExit) as exc:
        _record(svc, "--type", "L3", *extra)
    assert exc.value.code == 1
    assert svc.be.rows == []
    err = capsys.readouterr().err
    assert says in err and "SENAR Rule 4" in err


@pytest.mark.parametrize(
    "model_id, family",
    [
        ("glm-5.2", "glm:glm-5.2"),
        ("zai-coding-plan/glm-5.2", "glm:glm-5.2"),
        ("glm-5.2 [200k]", "glm:glm-5.2"),
        ("glm-4.5-air", "glm:haiku"),
        ("glm-x", None),
    ],
    ids=["bare", "provider-prefixed", "window-suffixed", "registered-starter", "invented"],
)
def test_a_released_glm_generation_is_recognized_in_every_host_spelling(model_id, family):
    assert rs.review_model_family(model_id) == family


@pytest.mark.parametrize(
    "author, reviewer, vendor",
    [
        ("claude-sonnet-4-6", "claude-opus-4-8", "claude"),
        ("claude-opus-5-5", "claude-opus-5-5", "claude"),
        ("glm-4.5-air", "glm-5.2", "glm"),
        ("gpt-5.6-sol", "gpt-6-astra", "openai"),
        ("zai-coding-plan/glm-5.2", "glm-5.2 [200k]", "glm"),
    ],
    ids=["claude-tiers", "same-id", "glm-generations", "openai-tiers", "host-spellings"],
)
def test_one_environment_family_covers_tiers_and_generations(author, reviewer, vendor):
    assert rs.vendor_family(author) == rs.vendor_family(reviewer) == vendor


@pytest.mark.parametrize(
    "author, reviewer",
    [
        ("glm-5.2", "glm-5.2"),
        ("gpt-5.6-sol", "gpt-6-astra"),
    ],
    ids=["glm-same-model", "openai-tiers"],
)
def test_a_same_family_l3_is_the_recordable_form(author, reviewer):
    svc = _Svc()
    _record(svc, "--type", "L3", "--author-model", author, "--reviewer-model", reviewer)
    assert svc.be.rows[0]["author_model"] == author
    assert svc.be.rows[0]["reviewer_model"] == reviewer
    assert svc.be.rows[0]["reviewer_context"] == "external"


def test_an_l3_within_one_vendor_family_is_recorded_with_both_models():
    svc = _Svc()
    _record(
        svc, "--type", "L3", "--author-model", "claude-opus-5-5",
        "--reviewer-model", "claude-fable-5-1", "--notes", "verdict=approved",
    )  # fmt: skip
    assert svc.be.rows[0]["notes"] == (
        "author_model=claude-opus-5-5 reviewer_model=claude-fable-5-1\nverdict=approved"
    )


@pytest.mark.parametrize("level", ["L1", "L2"])
def test_l1_and_l2_need_no_models(level):
    svc = _Svc()
    _record(svc, "--type", level, "--warnings", "1")
    assert svc.be.rows[0]["notes"] is None


def test_the_invitation_carries_the_author_id_and_the_one_family_rule():
    hint = er.reviewer_hint("claude-opus-5-5")
    assert "Author model: claude-opus-5-5" in hint
    assert "--author-model" in hint and "--reviewer-model" in hint
    assert "SAME model family" in hint
    assert "prohibited" in hint
