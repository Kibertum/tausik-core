"""A lane whose redness nobody reads is a lane that is switched off.

On 2026-08-25 three `windows-latest` jobs of the release verification workflow
went red. The run stayed red for nine days, and the commits publishing the 1.9
work went out over it. Nothing alerted, and nothing in the toolchain ever asked.

The verdict is now printed at the chokepoint of PUBLISHING — `push-ok`, the one
command that already stands before every push and already needs the network.

What these tests pin is not the happy path. It is the shape of the answer when
the check CANNOT run: every such case must say so, in words, with a reason. A
check that reports silence as health is the defect this release keeps finding,
and it would be worse here than no check at all — it would retire the question.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_TESTS, "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import ci_lane_status  # noqa: E402


def _gh_returning(rc, stdout="", stderr=""):
    def fake(argv, timeout):
        return rc, stdout, stderr

    return fake


def _one_run(**over):
    run = {
        "databaseId": 32895740027,
        "conclusion": "failure",
        "status": "completed",
        "headBranch": "main",
        "createdAt": "2026-08-25T20:30:45Z",
    }
    run.update(over)
    return json.dumps([run])


class TestTheSlug:
    @pytest.mark.parametrize(
        "remotes,expected",
        [
            ("github\thttps://github.com/Kibertum/tausik-core.git (fetch)", "Kibertum/tausik-core"),
            ("origin\tgit@github.com:Kibertum/tausik-core.git (push)", "Kibertum/tausik-core"),
            ("origin\thttps://gitlab.example.internal/a/b/c.git (fetch)", None),
            ("", None),
        ],
    )
    def test_the_github_remote_is_recognised(self, remotes, expected):
        assert ci_lane_status.github_slug(remotes) == expected

    def test_a_gitlab_only_repo_is_reported_as_unchecked_not_as_green(self):
        state, message = ci_lane_status.report("origin\thttps://gitlab.example/x/y.git (fetch)")
        assert state == "unknown"
        assert "not checked" in message


class TestTheVerdict:
    def test_a_red_lane_is_reported_red_with_run_and_date(self, monkeypatch):
        monkeypatch.setattr(ci_lane_status, "_run", _gh_returning(0, _one_run()))
        state, message = ci_lane_status.describe("o/r")
        assert state == "fail"
        assert "FAILURE" in message
        assert "32895740027" in message
        assert "2026-08-25" in message

    def test_a_green_lane_is_reported_green(self, monkeypatch):
        monkeypatch.setattr(
            ci_lane_status, "_run", _gh_returning(0, _one_run(conclusion="success"))
        )
        state, message = ci_lane_status.describe("o/r")
        assert state == "pass"
        assert "GREEN" in message

    def test_a_run_still_going_is_neither_pass_nor_fail(self, monkeypatch):
        monkeypatch.setattr(
            ci_lane_status,
            "_run",
            _gh_returning(0, _one_run(status="in_progress", conclusion=None)),
        )
        state, _message = ci_lane_status.describe("o/r")
        assert state == "running"


class TestCouldNotRunIsNeverPassed:
    """The property that makes this check worth having."""

    @pytest.mark.parametrize(
        "rc,stdout,stderr,needle",
        [
            (127, "", "not found", "not installed"),
            (124, "", "timed out", "timed out"),
            (1, "", "HTTP 401: Bad credentials", "gh failed"),
            (0, "not json at all", "", "unreadable"),
            (0, "[]", "", "nothing to report"),
            (0, json.dumps([{"databaseId": 7, "status": "completed"}]), "", "unreadable"),
        ],
    )
    def test_every_failure_to_read_says_so(self, monkeypatch, rc, stdout, stderr, needle):
        monkeypatch.setattr(ci_lane_status, "_run", _gh_returning(rc, stdout, stderr))
        state, message = ci_lane_status.describe("o/r")
        assert state == "unknown", message
        assert needle in message

    def test_no_unreadable_case_can_report_pass(self, monkeypatch):
        """Stated as a rule over the cases, not one assertion per case."""
        for rc, stdout in ((127, ""), (124, ""), (1, ""), (0, "garbage"), (0, "[]")):
            monkeypatch.setattr(ci_lane_status, "_run", _gh_returning(rc, stdout))
            state, _ = ci_lane_status.describe("o/r")
            assert state != "pass"

    def test_a_missing_slug_is_unknown_rather_than_silent(self):
        state, message = ci_lane_status.describe(None)
        assert state == "unknown"
        assert message.strip()


class TestPushOkPrintsItAndStillIssuesTheTicket:
    def test_the_ticket_is_written_even_when_the_lane_cannot_be_read(
        self, tmp_path, monkeypatch, capsys
    ):
        """Reporting must never cost the push it stands in front of."""
        import cli_push_ok

        (tmp_path / ".tausik").mkdir()
        monkeypatch.chdir(tmp_path)
        # `_git_detail` is the seam now: `cmd_push_ok` needs the REASON a git
        # query failed, not only its value, so that a refusal can name what
        # actually happened instead of asserting a cause nobody checked.
        monkeypatch.setattr(
            cli_push_ok,
            "_git_detail",
            lambda args: (("a" * 40, "") if args[:1] == ["rev-parse"] else ("", "")),
        )
        monkeypatch.setattr(ci_lane_status, "_run", _gh_returning(127, "", "not found"))

        class _Args:
            ttl = 60

        cli_push_ok.cmd_push_ok(None, _Args())
        out = capsys.readouterr().out
        assert "push ticket written" in out
        assert "CI:" in out
        assert "not checked" in out
        assert (tmp_path / ".tausik" / cli_push_ok.TICKET_FILENAME).exists()

    def test_a_red_lane_is_printed_but_does_not_refuse_the_ticket(
        self, tmp_path, monkeypatch, capsys
    ):
        """Whether to publish over red is the owner's call, not the tool's."""
        import cli_push_ok

        (tmp_path / ".tausik").mkdir()
        monkeypatch.chdir(tmp_path)
        # Two seams now. `cmd_push_ok` asks `_git_detail` for HEAD because it
        # needs the REASON when the query fails; the remote lookup still goes
        # through `_git`. Stubbing only the old one left the real git running
        # in a tmp dir that is not a repository — which the new diagnostic
        # reported precisely, and that is how this was found.
        monkeypatch.setattr(
            cli_push_ok,
            "_git_detail",
            lambda args: (("b" * 40, "") if args[:1] == ["rev-parse"] else ("", "")),
        )
        monkeypatch.setattr(
            cli_push_ok,
            "_git",
            lambda args: (
                "b" * 40
                if args[:1] == ["rev-parse"]
                else "github\thttps://github.com/o/r.git (fetch)"
            ),
        )
        monkeypatch.setattr(ci_lane_status, "_run", _gh_returning(0, _one_run()))

        class _Args:
            ttl = 60

        cli_push_ok.cmd_push_ok(None, _Args())
        out = capsys.readouterr().out
        assert "FAILURE" in out
        assert "your call" in out
        assert (tmp_path / ".tausik" / cli_push_ok.TICKET_FILENAME).exists()
