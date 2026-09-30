"""An L3 review record proves separation of duties or is refused (github#157).

l3-dispatch-does-not-carry-the-author-model (1.10). Before, `review record
--type L3` stored free notes only; a reviewer on the author's own model closed
the review gate as well as any other.
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
        (["--author-model", "claude-opus-5-5", "--reviewer-model", "opus"], "same family"),
        (["--author-model", "claude-opus-5-5"], "--reviewer-model"),
        (["--reviewer-model", "claude-fable-5-1"], "--author-model"),
        (["--author-model", "claude-opus-5-5", "--reviewer-model", "gpt-x"], "not a recognised"),
    ],
    ids=["same-family", "no-reviewer", "unknown-author", "unknown-reviewer"],
)
def test_an_l3_without_shown_separation_is_refused_and_not_written(extra, says, capsys):
    svc = _Svc()
    with pytest.raises(SystemExit) as exc:
        _record(svc, "--type", "L3", *extra)
    assert exc.value.code == 1
    assert svc.be.rows == []
    err = capsys.readouterr().err
    assert says in err and "SENAR Rule 4" in err


def test_an_l3_on_a_different_family_is_recorded_with_both_models():
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


def test_the_invitation_carries_the_author_id_and_the_record_flags():
    hint = er.reviewer_hint("claude-opus-5-5")
    assert "Author model: claude-opus-5-5" in hint
    assert "--author-model" in hint and "--reviewer-model" in hint
