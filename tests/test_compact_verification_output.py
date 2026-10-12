"""The model sees a bounded verify answer while the project keeps the whole run."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_runner import format_results
from render_verify import verify_lines
from verify_compact_output import _test_counts


class _Service:
    def __init__(self, root):
        self._root = root

    def tausik_dir(self):
        return str(self._root / ".tausik")


def _report(*, passed, results, run_id=71):
    return {
        "passed": passed,
        "status": "miss",
        "trigger": "verify",
        "run_id": run_id,
        "relevant_files": [],
        "results": results,
    }


def _gate(name, *, passed, output, skipped=False):
    return {
        "name": name,
        "passed": passed,
        "skipped": skipped,
        "severity": "block",
        "output": output,
    }


def test_large_success_answer_is_compact_but_artifact_retains_every_byte(tmp_path):
    output = "progress\n" * 800 + "= 120 passed, 4 skipped, 8 deselected in 1.00s =\n"
    results = [_gate("pytest", passed=True, output=output)] + [
        _gate(f"static-{n}", passed=True, output="") for n in range(120)
    ]
    report = _report(passed=True, results=results)

    rendered = "\n".join(verify_lines(_Service(tmp_path), report, None, "full"))
    artifact = tmp_path / ".tausik" / "verification" / "verify-71.log"
    counts_artifact = artifact.with_suffix(".json")
    historical_visible = "Verify (scope=full, task=-): passed=True\n" + format_results(results)

    assert "Verify (scope=full, task=-): PASS" in rendered
    assert "denominator=full-suite" in rendered
    assert "tests(passed=120, skipped=4, deselected=8)" in rendered
    assert output in artifact.read_text(encoding="utf-8")
    counts = json.loads(counts_artifact.read_text(encoding="utf-8"))
    assert counts["schema_version"] == 1
    assert counts["verdict"] == "PASS"
    assert counts["tests"] == {"passed": 120, "skipped": 4, "deselected": 8}
    assert counts["gates"][-1]["name"] == "static-119"
    assert counts["log"] == ".tausik/verification/verify-71.log"
    assert "Machine counts: .tausik/verification/verify-71.json" in rendered
    assert len(rendered.encode("utf-8")) * 3 < len(historical_visible.encode("utf-8")), rendered


def test_evidence_prefers_complete_artifact_output_over_display_excerpt(tmp_path):
    report = _report(
        passed=False,
        results=[
            _gate("ruff", passed=False, output="short display")
            | {"artifact_output": "complete lint output\nline two"}
        ],
        run_id=77,
    )

    rendered = "\n".join(verify_lines(_Service(tmp_path), report, None, "standard"))
    artifact = tmp_path / ".tausik" / "verification" / "verify-77.log"

    assert "short display" in rendered
    assert "complete lint output\nline two" in artifact.read_text(encoding="utf-8")


def test_failed_answer_is_bounded_and_does_not_make_unknown_counts_zero(tmp_path):
    results = [
        _gate(f"gate-{n}", passed=False, output="line\n" * 10 + f"failure {n}\n") for n in range(5)
    ]
    report = _report(passed=False, results=results, run_id=72)

    rendered = "\n".join(verify_lines(_Service(tmp_path), report, None, "standard"))
    artifact = tmp_path / ".tausik" / "verification" / "verify-72.log"

    assert "Verify (scope=standard, task=-): FAIL" in rendered
    assert "tests(passed=unknown, skipped=unknown, deselected=unknown)" in rendered
    assert "Actionable failures: showing 3/5" in rendered
    assert "… 2 more failure(s) omitted" in rendered
    assert "output truncated after 4 lines" in rendered
    full = artifact.read_text(encoding="utf-8")
    assert "[FAIL] gate-4" in full and "failure 4" in full


def test_skipped_gate_remains_visible_and_cannot_change_service_failure(tmp_path):
    report = _report(
        passed=False,
        results=[
            _gate("pytest", passed=True, skipped=True, output="5 deselected"),
            _gate("ruff", passed=False, output="bad style"),
        ],
        run_id=73,
    )

    rendered = "\n".join(verify_lines(_Service(tmp_path), report, None, "full"))

    assert "Verify (scope=full, task=-): FAIL" in rendered
    assert "Skipped gates: pytest did NOT execute" in rendered
    assert "tests(passed=unknown, skipped=unknown, deselected=5)" in rendered


def test_one_huge_diagnostic_line_cannot_expand_the_bounded_failure_answer(tmp_path):
    report = _report(
        passed=False, results=[_gate("pytest", passed=False, output="x" * 20_000)], run_id=74
    )

    rendered = "\n".join(verify_lines(_Service(tmp_path), report, None, "full"))

    assert len(rendered.encode("utf-8")) < 2_000
    assert "output truncated" in rendered


def test_failure_excerpt_keeps_pytest_tail_identity_and_trusted_scope(tmp_path):
    output = (
        "header\n" * 20
        + "FAILED tests/test_real.py::test_real - assertion\n= 1 failed, 9 passed in 1s =\n"
    )
    report = _report(
        passed=False,
        results=[_gate("pytest", passed=False, output=output) | {"scope": "2 of 403 test files"}],
        run_id=75,
    )

    rendered = "\n".join(verify_lines(_Service(tmp_path), report, None, "standard"))
    evidence = (tmp_path / ".tausik" / "verification" / "verify-75.log").read_text(encoding="utf-8")

    assert "denominator=2 of 403 test files" in rendered
    assert "FAILED tests/test_real.py::test_real" in rendered
    assert "Scope: 2 of 403 test files" in evidence


def test_frozen_full_lane_tail_keeps_deselected_when_final_summary_omits_it(tmp_path):
    output = (
        "143 deselected (not run) -- markexpr 'not slow'; the slow lane is `pytest -m slow`\n"
        "=========================== short test summary info ===========================\n"
        "FAILED tests/test_gate_ruff_format.py::test_the_legacy_list_only_shrinks - AssertionError\n"
        "1 failed, 12622 passed, 34 skipped, 62 warnings in 125.26s (0:02:05)\n"
    )
    report = _report(
        passed=False, results=[_gate("pytest", passed=False, output=output)], run_id=76
    )

    rendered = "\n".join(verify_lines(_Service(tmp_path), report, None, "full"))

    assert "tests(passed=12622, skipped=34, deselected=143)" in rendered


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (
            "bringing up nodes...\n10 passed in 1.0s\n",
            {"passed": 10, "skipped": None, "deselected": None},
        ),
        (
            "bringing up nodes...\n10 passed in 1.0s\nbringing up nodes...\n7 passed, 2 skipped in 1.0s\n",
            {"passed": 17, "skipped": 2, "deselected": None},
        ),
        (
            "bringing up nodes...\n10 passed in 1.0s\n10 passed in 1.0s\n",
            {"passed": 10, "skipped": None, "deselected": None},
        ),
        (
            "bringing up nodes...\n3 deselected (not run)\n10 passed in 1.0s\nbringing up nodes...\n5 passed in 1.0s\n",
            {"passed": 15, "skipped": None, "deselected": 3},
        ),
    ],
    ids=["single", "multibatch", "echo", "multiline_deselected"],
)
def test_pytest_batch_count_matrix(output, expected):
    assert _test_counts([_gate("pytest", passed=True, output=output)]) == expected


def test_verify_3330_frozen_batch_summaries_add_to_the_live_total():
    # Exact terminal summaries from .tausik/verification/verify-3330.log.
    counts = [
        70,
        66,
        32,
        42,
        329,
        60,
        156,
        91,
        68,
        77,
        75,
        70,
        42,
        40,
        63,
        46,
        60,
        63,
        99,
        202,
        86,
        51,
        85,
        85,
        58,
    ]
    output = "\n".join(f"bringing up nodes...\n{count} passed in 1.0s" for count in counts)
    output = output.replace("329 passed in 1.0s", "329 passed, 12 skipped in 1.0s")

    assert _test_counts([_gate("pytest", passed=True, output=output)]) == {
        "passed": 2116,
        "skipped": 12,
        "deselected": None,
    }


def test_evidence_write_failure_is_explicit_and_does_not_crash(tmp_path, monkeypatch):
    import verify_compact_output

    monkeypatch.setattr(
        verify_compact_output.Path,
        "mkdir",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("read-only")),
    )
    rendered = "\n".join(
        verify_lines(_Service(tmp_path), _report(passed=True, results=[]), None, "full")
    )

    assert "Verify (scope=full, task=-): PASS" in rendered
    assert "Full evidence: UNAVAILABLE" in rendered
