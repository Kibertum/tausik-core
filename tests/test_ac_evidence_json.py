"""v14b-token-t15: --evidence-json structured evidence for task_done.

Round-trip: JSON → canonical prose → parse_evidence_lines / build_report
produces equivalent AcCoverageReport to a hand-written prose entry.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from service_ac_evidence import (  # noqa: E402
    build_report,
    evidence_json_to_prose,
)
from tausik_utils import ServiceError  # noqa: E402


# ---- positive cases -------------------------------------------------------


def test_minimal_single_ac_pass():
    raw = '{"ac_evidence":[{"n":1,"status":"pass","evidence":"tests/foo.py::ok"}]}'
    prose = evidence_json_to_prose(raw)
    assert prose.startswith("AC verified:")
    assert "1. ✓ tests/foo.py::ok" in prose


def test_three_ac_all_pass_round_trip():
    raw = (
        '{"ac_evidence":['
        '{"n":1,"status":"pass","evidence":"tests/test_a.py::test_one"},'
        '{"n":2,"status":"pass","evidence":"tests/test_b.py::test_two"},'
        '{"n":3,"status":"pass","evidence":"manual smoke run"}'
        "]}"
    )
    prose = evidence_json_to_prose(raw)
    ac_text = "1. First\n2. Second\n3. Third"
    rep = build_report(ac_text, prose)
    assert rep.total_ac == 3
    assert rep.covered == 3
    assert rep.gaps() == []


def test_mixed_pass_fail_leaves_gap():
    raw = (
        '{"ac_evidence":['
        '{"n":1,"status":"pass","evidence":"tests/test_a.py::test_one"},'
        '{"n":2,"status":"fail","evidence":"flaky on Windows"}'
        "]}"
    )
    prose = evidence_json_to_prose(raw)
    assert "FAIL:" in prose
    rep = build_report("1. First\n2. Second", prose)
    # The fail line carries no checkmark + no test ref → AC-2 has no
    # evidence_type != none, so it stays a gap.
    assert 2 in rep.gaps()
    assert 1 not in rep.gaps()


def test_manual_flag_emits_marker():
    raw = (
        '{"ac_evidence":[{"n":1,"status":"pass","evidence":"smoke run on staging","manual":true}]}'
    )
    prose = evidence_json_to_prose(raw)
    assert "manual" in prose.lower()
    rep = build_report("1. Endpoint works", prose)
    assert rep.items[0].has_manual is True


def test_negative_flag_emits_marker():
    raw = (
        '{"ac_evidence":['
        '{"n":1,"status":"pass","evidence":"401 returned for bad creds","negative":true}'
        "]}"
    )
    prose = evidence_json_to_prose(raw)
    assert "negative" in prose.lower()
    rep = build_report("1. Auth blocks invalid creds", prose)
    assert rep.has_negative_evidence is True


# ---- negative cases -------------------------------------------------------


@pytest.mark.parametrize(
    "raw,match_pattern",
    [
        pytest.param('{"ac_evidence":[bogus', "invalid --evidence-json", id="malformed_json"),
        pytest.param("", "empty input", id="empty_input"),
        pytest.param("[]", "top-level must be an object", id="top_level_not_object"),
        pytest.param('{"foo": "bar"}', "'ac_evidence' must be a list", id="missing_ac_evidence"),
        pytest.param('{"ac_evidence": []}', "'ac_evidence' is empty", id="ac_evidence_empty_list"),
        pytest.param(
            '{"ac_evidence":[{"status":"pass","evidence":"x"}]}',
            r"\.n must be a positive integer",
            id="item_missing_n",
        ),
        pytest.param(
            '{"ac_evidence":[{"n":0,"status":"pass","evidence":"x"}]}',
            r"\.n must be a positive integer",
            id="item_n_zero",
        ),
        pytest.param(
            # bool is subclass of int — must be excluded.
            '{"ac_evidence":[{"n":true,"status":"pass","evidence":"x"}]}',
            r"\.n must be a positive integer",
            id="item_n_bool",
        ),
        pytest.param(
            '{"ac_evidence":[{"n":1,"status":"maybe","evidence":"x"}]}',
            r"\.status must be 'pass' or 'fail'",
            id="item_status_invalid",
        ),
        pytest.param(
            '{"ac_evidence":[{"n":1,"status":"pass"}]}',
            r"\.evidence must be a non-empty string",
            id="item_evidence_missing",
        ),
        pytest.param(
            '{"ac_evidence":[{"n":1,"status":"pass","evidence":"   "}]}',
            r"\.evidence must be a non-empty string",
            id="item_evidence_blank",
        ),
        pytest.param(
            '{"ac_evidence":["just-a-string"]}',
            r"ac_evidence\[0\] must be an object",
            id="item_not_object",
        ),
    ],
)
def test_validation_raises(raw, match_pattern):
    with pytest.raises(ServiceError, match=match_pattern):
        evidence_json_to_prose(raw)


# ---- security: SQL-flavored payload is treated as opaque text -------------


def test_sql_payload_is_inert_in_prose():
    """Agent-controlled evidence must not become live SQL.

    The string travels through json.loads (no eval) → prose → task_log
    (parameterised insert). This test only asserts it survives the helper
    intact; the SQL safety is the parameterised insert in task_log itself.
    """
    payload = "tests/x.py'); DROP TABLE tasks;--"
    raw = f'{{"ac_evidence":[{{"n":1,"status":"pass","evidence":"{payload}"' + "}]}"
    prose = evidence_json_to_prose(raw)
    assert payload in prose


# ---- mutex: tested at service layer, not helper ---------------------------


def test_service_layer_mutex_prose_and_json(tmp_path):
    """task_done with both --evidence and --evidence-json must reject.

    Mutex check fires before _require_task, so the test does not need a
    seeded task — a fresh ProjectService is enough.
    """
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    svc = ProjectService(SQLiteBackend(str(tmp_path / "t.db")))

    with pytest.raises(ServiceError, match="mutually exclusive"):
        svc._task_done_report(
            "nonexistent",
            relevant_files=None,
            ac_verified=True,
            no_knowledge=True,
            evidence="AC verified: 1. ✓",
            evidence_json='{"ac_evidence":[{"n":1,"status":"pass","evidence":"x"}]}',
        )
