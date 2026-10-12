"""A failed gate's report names the failing tests (github#11, task A of 1.10).

The verify report printed the first five lines of a failed gate's output. A
batched pytest run starts with "bringing up nodes..." and progress dots and
puts FAILED names and "N failed" at the end, so the report said
`[FAIL] pytest (block)` over dots and nothing else — measured in sessions #263
and #266, where the red test was found only by re-running the selection by hand.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from gate_runner import failure_excerpt, format_results  # noqa: E402

_BATCHED = "\n".join(
    ["bringing up nodes...", "bringing up nodes...", "", "80 passed in 7.09s"]
    + ["bringing up nodes..."] * 3
    + ["." * 72 + " [ 90%]"] * 6
    + [
        "=========================== short test summary info ===========================",
        "FAILED tests/test_mcp_surface_ratchet.py::TestX::test_surface_is_within_the_baseline",
        "!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!",
        "1 failed, 43 passed in 6.83s",
        "bringing up nodes...",
        "bringing up nodes...",
        "",
        "." * 72 + " [100%]",
        "70 passed in 7.04s",
        "",
    ]
)


def _report(output: str, passed: bool = False) -> str:
    return format_results(
        [{"name": "pytest", "passed": passed, "severity": "block", "output": output}]
    )


def test_the_failing_test_name_reaches_the_report():
    text = _report(_BATCHED)
    assert (
        "FAILED tests/test_mcp_surface_ratchet.py::TestX::test_surface_is_within_the_baseline"
        in text
    )
    assert "1 failed, 43 passed in 6.83s" in text


def test_the_old_head_alone_would_have_lost_it():
    """The defect, pinned: the first five lines do not contain the name."""
    assert not any("FAILED" in line for line in _BATCHED.split("\n")[:5])


def test_output_without_pytest_lines_keeps_head_and_tail():
    """NEGATIVE: another tool's long output is not reduced to nothing."""
    body = "\n".join(f"line {i}" for i in range(40))
    out = failure_excerpt(body)
    assert out[0] == "line 0" and out[-1] == "line 39" and "..." in out


def test_a_passing_gate_prints_no_body():
    """NEGATIVE: the excerpt is for failures only."""
    assert "FAILED" not in _report(_BATCHED, passed=True)


def test_short_output_is_printed_whole():
    assert failure_excerpt("a\nb\nc") == ["a", "b", "c"]
