"""SENAR 1.5 §10.15(f): the severity scale is documented, the reviewers use it,
and CRITICAL is recorded with its reason (severity-scale-is-documented-and-used-by-review)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from project_cli_review import cmd_review  # noqa: E402
from project_parser import build_parser  # noqa: E402

PAGES = [ROOT / "docs" / "en" / "severity-scale.md", ROOT / "docs" / "ru" / "severity-scale.md"]
READERS = [
    ROOT / "harness" / "skills" / "review" / "SKILL.md",
    ROOT / "harness" / "claude" / "subagents" / "tausik-reviewer.md",
    ROOT / "harness" / "claude" / "subagents" / "tausik-external-reviewer.md",
]


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.parent.name)
def test_the_page_defines_the_levels_and_says_which_scale_it_is(page):
    text = page.read_text(encoding="utf-8")
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        assert f"**{level}**" in text
    assert "§8.7" in text and "§10.15(f)" in text and "tier" in text
    assert "§10.15(a)" in text  # who decides for an L3 finding


@pytest.mark.parametrize("reader", READERS, ids=lambda p: p.stem)
def test_the_review_skill_and_both_reviewers_cite_the_page(reader):
    assert "docs/en/severity-scale.md" in reader.read_text(encoding="utf-8")


class _Be:
    def __init__(self):
        self.rows: list[dict] = []

    def review_record(self, **kw):
        self.rows.append(kw)
        return len(self.rows)

    def review_list(self, **_):
        return [
            {
                "id": i + 1,
                "run_type": r["run_type"],
                "task_slug": r["task_slug"],
                "critical_findings": r["critical_findings"],
                "warnings": r["warnings"],
                "run_at": "2026-09-23",
                "notes": r["notes"],
            }
            for i, r in enumerate(self.rows)
        ]


class _Svc:
    def __init__(self):
        self.be = _Be()

    def task_show(self, slug):
        return {"slug": slug}


def _args(*argv):
    return build_parser().parse_args(["review", *argv])


def test_critical_without_a_reason_is_refused_and_nothing_is_written(capsys):
    svc = _Svc()
    with pytest.raises(SystemExit) as exc:
        cmd_review(svc, _args("record", "--task", "t", "--type", "L3", "--critical", "1"))
    assert exc.value.code == 1
    assert svc.be.rows == []
    err = capsys.readouterr().err
    assert "--critical 1 needs --reason" in err
    assert "docs/en/severity-scale.md" in err


def test_critical_with_a_reason_is_recorded_and_listed(capsys):
    svc = _Svc()
    cmd_review(
        svc,
        _args(
            "record", "--task", "t", "--type", "L2", "--critical", "1",
            "--reason", "hook fails open", "--notes", "pr#9",
        ),
    )  # fmt: skip
    assert svc.be.rows[0]["notes"] == "CRITICAL reason: hook fails open\npr#9"
    cmd_review(svc, _args("list"))
    assert "CRITICAL reason: hook fails open" in capsys.readouterr().out


def test_zero_critical_needs_no_reason():
    svc = _Svc()
    cmd_review(svc, _args("record", "--task", "t", "--type", "L2", "--warnings", "3"))
    assert svc.be.rows[0]["notes"] is None

