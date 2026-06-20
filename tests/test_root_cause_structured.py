"""v15s-rule7-rootcause-hardgate: structured root cause (decision #96).

The keyword floor (test_failclosed_root_cause.py) stays a hard gate. This
covers the *structured* layer on top: parser, coverage metric, and the
advisory escalating nudge fired when a defect satisfies the keyword floor
but is not yet in `category + description + prevention` form.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from root_cause import (  # noqa: E402
    ROOT_CAUSE_CATEGORIES,
    has_structured_root_cause,
    parse_root_cause,
    root_cause_metrics,
)

_STRUCTURED = "Root cause (logic-error): off-by-one in pager. Prevention: add bounds test."


class TestParseRootCause:
    def test_valid_structured(self):
        rc = parse_root_cause(_STRUCTURED)
        assert rc == {
            "category": "logic-error",
            "description": "off-by-one in pager.",
            "prevention": "add bounds test.",
        }

    def test_russian_keywords(self):
        rc = parse_root_cause(
            "Причина (race-condition): гонка при инициализации. Профилактика: лок."
        )
        assert rc is not None
        assert rc["category"] == "race-condition"

    def test_unknown_category_not_structured(self):
        # AC4: unknown category -> not structured, no exception
        assert parse_root_cause("Root cause (banana): x. Prevention: y.") is None

    def test_keyword_only_not_structured(self):
        # The keyword floor passes this, but it is not the structured form.
        assert parse_root_cause("Root cause: off-by-one in pagination") is None

    def test_missing_prevention_not_structured(self):
        assert parse_root_cause("Root cause (config-error): hardcoded timeout.") is None

    def test_empty_and_none(self):
        assert parse_root_cause(None) is None
        assert parse_root_cause("") is None

    def test_embedded_in_log_blob(self):
        notes = f"[2026-06-13T10:00:00Z] started\n[2026-06-13T10:05:00Z] {_STRUCTURED}\n"
        assert has_structured_root_cause(notes) is True

    def test_all_categories_parse(self):
        for cat in ROOT_CAUSE_CATEGORIES:
            notes = f"Root cause ({cat}): desc here. Prevention: do thing."
            assert parse_root_cause(notes) is not None, cat

    def test_label_form_dash_accepted(self):
        # rule7-rootcause-nag-inline-template: bracket-less label form.
        rc = parse_root_cause(
            "Root cause — logic-error: off-by-one in pager. Prevention: add bounds test."
        )
        assert rc == {
            "category": "logic-error",
            "description": "off-by-one in pager.",
            "prevention": "add bounds test.",
        }

    def test_label_form_colon_then_dash_accepted(self):
        rc = parse_root_cause("Root cause: race-condition — init race. Prevention: take the lock.")
        assert rc == {
            "category": "race-condition",
            "description": "init race.",
            "prevention": "take the lock.",
        }

    def test_label_form_all_categories_parse(self):
        for cat in ROOT_CAUSE_CATEGORIES:
            notes = f"Root cause — {cat}: desc here. Prevention: do thing."
            assert parse_root_cause(notes) is not None, cat

    def test_label_form_unknown_category_rejected(self):
        # No brackets + an out-of-list token must NOT parse (avoids a free-text
        # description masquerading as a category).
        assert parse_root_cause("Root cause — banana: x. Prevention: y.") is None


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TAUSIK_QUIET", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    s.task_add(None, "parent", "Parent task")
    return s


def _add_defect(svc, slug):
    svc.task_add(None, slug, "Defect fix", None, None, None, None, "parent")
    svc.task_update(
        slug,
        goal="g",
        acceptance_criteria="1. ok\n2. errors on bad input",
        scope="x.py",
    )
    svc.task_start(slug)


def _close(svc, slug):
    return svc.task_done(slug, None, True, False, evidence="AC verified: 1. OK 2. OK")


class TestRootCauseMetrics:
    def test_no_defect_tasks_no_zero_division(self, svc):
        # AC4: no defect tasks -> coverage 0.0, no ZeroDivisionError
        m = root_cause_metrics(svc.be._q)
        assert m == {"defect_done": 0, "structured": 0, "coverage_pct": 0.0}

    def test_coverage_mixed(self, svc):
        _add_defect(svc, "fix-structured")
        svc.task_log("fix-structured", _STRUCTURED)
        _close(svc, "fix-structured")

        _add_defect(svc, "fix-keyword")
        svc.task_log("fix-keyword", "Root cause: plain keyword only")
        _close(svc, "fix-keyword")

        m = root_cause_metrics(svc.be._q)
        assert m["defect_done"] == 2
        assert m["structured"] == 1
        assert m["coverage_pct"] == 50.0


class TestStructuredNudge:
    def test_keyword_only_fires_advisory_nudge(self, svc):
        _add_defect(svc, "fix-kw")
        svc.task_log("fix-kw", "Root cause: plain keyword only")
        msg = _close(svc, "fix-kw")
        assert "completed" in msg  # advisory — never blocks
        assert "structured form" in msg

    def test_structured_no_nudge(self, svc):
        _add_defect(svc, "fix-struct")
        svc.task_log("fix-struct", _STRUCTURED)
        msg = _close(svc, "fix-struct")
        assert "completed" in msg
        assert "structured form" not in msg
