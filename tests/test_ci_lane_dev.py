"""The development lane is read at the push chokepoint, and silence is never health.

MEASURED, session #277, and the numbers are why this module exists: the published
lane reader answered "GREEN" ten times in a row while naming a pipeline thirteen
days old, and over the same hours nine of the last ten pipelines on the working
branch were RED -- every push of the session. Worse, stages run in order, so the
red test stage left the full-battery job SKIPPED on all of them: the only lane that
reaches slow-marked tests never ran, which is how two deterministically broken
tests survived a release.

So the negative half is most of this file. A reader that reported "could not check"
as health would be worse than no reader, because it would retire the habit of
looking.

This test file is excluded from the public snapshot together with its subject.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import ci_lane_dev  # noqa: E402

GITHUB_ONLY = "github\thttps://github.com/Owner/repo.git (fetch)\n"
BOTH = GITHUB_ONLY + "origin\thttps://git.example.test/group/repo.git (fetch)\n"


def _client(monkeypatch, payload, rc=0, err="", jobs=None):
    """Stand in for the client: the listing, and the per-pipeline jobs call."""
    monkeypatch.setattr(ci_lane_dev.shutil, "which", lambda name: "/usr/bin/" + name)

    def fake(argv, timeout):
        if "get" in argv:
            body = json.dumps({"jobs": jobs or []})
            return 0, body, ""
        return rc, payload, err

    monkeypatch.setattr(ci_lane_dev, "_run", fake)


class TestNotCheckedIsNeverOk:
    """Each reason says what it was, and none of them is a pass."""

    def test_a_missing_client_says_so(self, monkeypatch):
        monkeypatch.setattr(ci_lane_dev.shutil, "which", lambda name: None)
        state, message = ci_lane_dev.describe("v1-10", BOTH)
        assert state == "unknown"
        assert "not installed" in message and "not green" in message

    def test_a_failing_client_quotes_its_own_reason(self, monkeypatch):
        _client(monkeypatch, "", rc=1, err="dial tcp: lookup failed")
        state, message = ci_lane_dev.describe("v1-10", BOTH)
        assert state == "unknown"
        assert "dial tcp: lookup failed" in message

    @pytest.mark.parametrize(
        ("branch", "payload", "expected"),
        [
            pytest.param("v1-10", "<html>not json</html>", "did not parse", id="malformed"),
            pytest.param("v1-10", "[]", "not a pass", id="no_pipeline_is_not_a_pass"),
            pytest.param("", "[]", "no branch name", id="no_branch"),
            pytest.param(
                "v1-10", '[{"id": 7, "status": "moon"}]', "unread", id="unrecognised_status"
            ),
        ],
    )
    def test_each_reason_names_itself(self, monkeypatch, branch, payload, expected):
        """Four routes, four different words. The wording IS the deliverable here.

        An empty history is the most tempting thing to render as green, and an
        unrecognised status the most tempting to round to the nearest colour.
        """
        _client(monkeypatch, payload)
        state, message = ci_lane_dev.describe(branch, BOTH)
        assert state == "unknown"
        assert expected in message

    @pytest.mark.parametrize(
        ("payload", "rc", "err"),
        [
            pytest.param("", 1, "boom", id="client_failed"),
            pytest.param("<html>", 0, "", id="unparseable"),
            pytest.param("[]", 0, "", id="no_pipeline"),
            pytest.param('[{"id": 1, "status": "moon"}]', 0, "", id="unknown_status"),
        ],
    )
    def test_no_unknown_is_reported_as_a_blank_line(self, monkeypatch, payload, rc, err):
        """A blank message renders as a blank line, which reads as nothing wrong.

        Every route to `unknown` is walked, because one silent route is enough to
        turn this reader back into the thing it replaced.
        """
        _client(monkeypatch, payload, rc=rc, err=err)
        state, message = ci_lane_dev.describe("v1-10", BOTH)
        assert state == "unknown"
        assert message.strip()


class TestTheColoursThemselves:
    def test_a_green_pipeline_reads_green(self, monkeypatch):
        _client(monkeypatch, json.dumps([{"id": 11, "status": "success"}]))
        assert ci_lane_dev.describe("v1-10", BOTH) == (
            "pass",
            "development lane on `v1-10` is GREEN (#11)",
        )

    def test_a_red_pipeline_names_the_verification_job(self, monkeypatch):
        _client(
            monkeypatch,
            json.dumps([{"id": 12, "status": "failed"}]),
            jobs=[{"name": "tests", "status": "failed"}],
        )
        state, message = ci_lane_dev.describe("v1-10", BOTH)
        assert state == "fail"
        assert "`tests` failed" in message

    def test_a_running_pipeline_is_neither_pass_nor_fail(self, monkeypatch):
        _client(monkeypatch, json.dumps([{"id": 13, "status": "running"}]))
        assert ci_lane_dev.describe("v1-10", BOTH)[0] == "running"


class TestTheSkippedBatteryIsTheFinding:
    """A colour that never ran the tests must not be reported as a colour about them.

    This is the single most expensive thing the measurement found, so it is pinned
    hardest: `tests-full` skipped means the slow lane did not run, and saying so is
    the difference between "green" and "green about something else".
    """

    @pytest.mark.parametrize("job_status", ["skipped", "manual", "created"])
    def test_an_unrun_battery_is_called_out(self, monkeypatch, job_status):
        _client(
            monkeypatch,
            json.dumps([{"id": 14, "status": "failed"}]),
            jobs=[{"name": "tests-full", "status": job_status}],
        )
        _state, message = ci_lane_dev.describe("v1-10", BOTH)
        assert "were NOT run" in message
        assert job_status in message

    def test_a_battery_that_ran_adds_no_caveat(self, monkeypatch):
        _client(
            monkeypatch,
            json.dumps([{"id": 15, "status": "failed"}]),
            jobs=[{"name": "tests-full", "status": "success"}],
        )
        _state, message = ci_lane_dev.describe("v1-10", BOTH)
        assert "were NOT run" not in message

    def test_the_job_level_is_not_read_for_a_green_pipeline(self, monkeypatch):
        """One call on the common path. A green pipeline has already run everything.

        Asserted by refusing the second call outright: if `describe` reaches for the
        jobs of a green pipeline, this test fails rather than quietly costing a round
        trip on every push.
        """
        monkeypatch.setattr(ci_lane_dev.shutil, "which", lambda name: "/usr/bin/glab")

        def fake(argv, timeout):
            assert "get" not in argv, "a green pipeline must not cost a second call"
            return 0, json.dumps([{"id": 16, "status": "success"}]), ""

        monkeypatch.setattr(ci_lane_dev, "_run", fake)
        assert ci_lane_dev.describe("v1-10", BOTH)[0] == "pass"


class TestAConsumerHasNothingToCheck:
    """Absence of a development remote is the normal state, and reads as neither."""

    def test_github_only_is_skipped_silently(self):
        assert ci_lane_dev.describe("main", GITHUB_ONLY) == ("skip", "")

    def test_no_remotes_at_all_is_skipped(self):
        assert ci_lane_dev.has_dev_remote("") is False

    def test_a_non_github_remote_is_recognised(self):
        assert ci_lane_dev.has_dev_remote(BOTH) is True


class TestReportingNeverRaises:
    """Rule 3: nothing here may cost a push ticket that lives sixty seconds."""

    def test_an_unexpected_fault_degrades_to_one_line(self, monkeypatch):
        def boom(*_a, **_k):
            raise RuntimeError("client exploded")

        monkeypatch.setattr(ci_lane_dev, "describe", boom)
        state, message = ci_lane_dev.report("v1-10", BOTH)
        assert state == "unknown"
        assert "RuntimeError" in message and "read it yourself" in message

    def test_a_timeout_is_an_answer_not_an_exception(self, monkeypatch):
        import subprocess

        def timing_out(*_a, **kw):
            raise subprocess.TimeoutExpired(cmd="glab", timeout=kw.get("timeout", 8))

        monkeypatch.setattr(ci_lane_dev.shutil, "which", lambda name: "/usr/bin/glab")
        monkeypatch.setattr(ci_lane_dev.subprocess, "run", timing_out)
        state, message = ci_lane_dev.describe("v1-10", BOTH, timeout=3)
        assert state == "unknown"
        assert "timed out" in message


class TestItStaysOffThePublicLine:
    """The owner's boundary, checked rather than promised."""

    def test_the_module_and_its_test_are_excluded_from_the_snapshot(self):
        from publication_snapshot import is_excluded

        assert is_excluded("scripts/ci_lane_dev.py")
        assert is_excluded("tests/test_ci_lane_dev.py")

    def test_the_host_is_derived_from_the_remote_rather_than_written_down(self):
        """No literal host, AND the derivation that makes the absence sustainable.

        Checking only for the absence of a literal would pass on a module that had
        no way to find the host at all. Both halves are asserted: nothing to redact,
        and a remote-driven path that keeps it that way, so the next person moving
        this code has nothing to remember.
        """
        source = (_REPO / "scripts" / "ci_lane_dev.py").read_text(encoding="utf-8")
        for literal in ("yumash", "https://gitlab", "gitlab.com"):
            assert literal not in source, literal
        assert "def has_dev_remote" in source
        assert "github.com" in source, "the remote is told apart by what it is NOT"

    def test_the_caller_prints_nothing_when_the_module_is_absent(self, monkeypatch, capsys):
        """In a published tree the import fails, and that must print nothing at all.

        The published `cli_push_ok` ships without this module, so an ImportError is
        the NORMAL case there rather than a fault worth a line of noise. Asserted on
        the OUTPUT, not merely on not raising: a stray "not checked" line in every
        consumer's push would be a defect of its own.
        """
        import cli_push_ok

        monkeypatch.setitem(sys.modules, "ci_lane_dev", None)
        cli_push_ok._report_dev_lane("  CI: ")
        assert capsys.readouterr().out == ""
