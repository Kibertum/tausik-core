"""Guards that keep the CI lanes honest — and that keep THIS repo's own workflow honest.

Two failures this project actually shipped motivate every assertion here:

  * The full (slow) lane was RED in main for a whole release, invisible because
    ``pyproject`` sets ``addopts = -m 'not slow'`` and CI ran a bare ``pytest tests/`` —
    i.e. the fast lane only. The release's own critical regression tests are slow-marked,
    so CI never ran them. A green badge over an untested third of the suite.
  * A hard ``ruff`` step ordered *before* the pytest step in the same job hid a Python
    3.13 incompatibility on a third of the matrix: ruff died first, pytest never ran, and
    the failure was masked until ruff was fixed.

So this file asserts, from the test suite itself (which the CI *does* run):
  1. the slow lane is not vacuous — there really are slow-marked tests, and a full
     collection sees strictly more than the fast lane. If someone drops the last slow
     marker, or a refactor makes ``-m ''`` and ``-m 'not slow'`` collect the same set,
     the "full lane" has silently become the fast lane and this test goes red.
  2. the workflow actually runs a full-lane job AND keeps lint decoupled from tests, so
     the two incidents above cannot recur structurally.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "tests.yml"

pytestmark = pytest.mark.slow  # spawns pytest --collect-only subprocesses


def _collect_count(marker_expr: str | None) -> int:
    """Number of tests pytest collects under an optional -m expression.

    ``--override-ini addopts=`` strips the inherited ``-m 'not slow'`` so we control the
    marker filter explicitly and measure the true lane sizes.
    """
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--collect-only",
        "-q",
        "--override-ini=addopts=",
        "-p",
        "no:cacheprovider",
    ]
    if marker_expr is not None:
        cmd += ["-m", marker_expr]
    proc = subprocess.run(
        cmd, cwd=str(_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300
    )
    # The trailing summary line: "N tests collected" (or "N/M tests collected").
    import re

    m = re.search(r"(\d+)(?:/\d+)?\s+tests?\s+collected", proc.stdout)
    assert m, f"could not parse collection count from:\n{proc.stdout[-500:]}\n{proc.stderr[-500:]}"
    return int(m.group(1))


class TestSlowLaneIsNotVacuous:
    def test_slow_marked_tests_exist(self):
        """If this hits zero, the 'full lane' is identical to the fast lane and the whole
        test-full CI job is a no-op guarding nothing."""
        slow = _collect_count("slow")
        assert slow > 0, (
            "no slow-marked tests exist — the full CI lane now equals the fast lane and "
            "gates nothing beyond it. Either a marker was dropped or the split is dead."
        )

    def test_full_lane_strictly_larger_than_fast_lane(self):
        """The full lane must see MORE than the default fast lane — otherwise CI running
        the fast lane already covers everything and the extra job is theatre."""
        full = _collect_count(None)  # -m absent → everything
        fast = _collect_count("not slow")
        assert full > fast, (
            f"full lane collects {full}, fast lane collects {fast}: they are not distinct, "
            "so `pytest tests/` already runs everything and the slow split is meaningless."
        )


def _job_blocks() -> dict[str, str]:
    """Split the workflow into {job_name: block_text} using STDLIB only.

    Deliberately NOT PyYAML: this project keeps PyYAML an optional dependency (see
    test_no_hard_yaml_import + the v1.5.0 fresh-clone smoke), and CI installs only pytest.
    A yaml-based guard would silently SKIP in CI — the exact blind spot this file exists to
    kill. The workflow format is ours, so a 2-space-indent block scan is enough and runs
    everywhere. A job is a 2-space-indented ``<name>:`` under the top-level ``jobs:`` key,
    its block running until the next such key.
    """
    text = _WORKFLOW.read_text(encoding="utf-8")
    lines = text.splitlines()
    # find the `jobs:` line (top-level, no indent)
    try:
        start = next(i for i, ln in enumerate(lines) if ln.rstrip() == "jobs:")
    except StopIteration:
        return {}
    blocks: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    def _flush():
        if current is not None:
            blocks[current] = "\n".join(buf)

    for ln in lines[start + 1 :]:
        stripped = ln.strip()
        # Comment lines DESCRIBE adjacent jobs (a comment above `test:` mentions pytest);
        # they are not commands and must not count toward what a job RUNS. Drop them, so a
        # job's block reflects its steps only — otherwise the lint block inherits the
        # next job's descriptive comment and looks like it runs pytest.
        if stripped.startswith("#"):
            continue
        # a job header: exactly two leading spaces, then `name:` (a comment can't be one,
        # already filtered above).
        if len(ln) > 2 and ln[:2] == "  " and ln[2] != " " and stripped.endswith(":"):
            _flush()
            current = stripped.rstrip(":")
            buf = []
        elif current is not None:
            buf.append(ln)
    _flush()
    return blocks


class TestWorkflowStructureIsHonest:
    """Static checks on .github/workflows/tests.yml — the repo's own CI must embody the
    lessons, not just document them. Stdlib-only, so these run in CI too."""

    def test_workflow_parses_into_jobs(self):
        blocks = _job_blocks()
        assert blocks, f"no jobs parsed from {_WORKFLOW}"

    def test_lint_is_a_separate_job_from_tests(self):
        """Lint decoupled from tests: a ruff failure must not be able to hide test results
        (the v1.7.0 masking incident). Enforced structurally — no single job runs both."""
        blocks = _job_blocks()
        lint_jobs = [n for n, t in blocks.items() if "ruff check" in t]
        test_jobs = [n for n, t in blocks.items() if "pytest" in t]
        assert lint_jobs, "no job runs `ruff check`"
        assert test_jobs, "no job runs pytest"
        overlap = set(lint_jobs) & set(test_jobs)
        assert not overlap, (
            f"jobs {overlap} run BOTH ruff and pytest — a hard ruff step there hides the "
            "pytest step (the v1.7.0 masking incident). Split lint into its own job."
        )

    def test_a_job_runs_the_full_slow_lane(self):
        """Some job must run the full lane (-m '' / -m 'slow'), or the slow-marked
        regression tests are never gated by CI."""
        joined = "\n".join(_job_blocks().values())
        runs_full = "-m ''" in joined or '-m ""' in joined or "-m 'slow'" in joined
        assert runs_full, (
            "no CI job runs the full lane (`pytest -m ''`). The slow-marked regression "
            "tests — the ones that catch this project's own critical bugs — go ungated."
        )
