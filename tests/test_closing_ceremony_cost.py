"""Closing a task costs one call, and the call still refuses what it should.

THE MEASUREMENT this was filed on. A close costs four to six calls: `verify`, `task done`,
a refusal from a gate that only fires at close, `verify` again, `task done` again. At the
project's measured 482 000 tokens of prefix re-sent per call, each extra call costs about
half a million tokens, and closing is the most frequent ceremony in the framework — 1240
closures carry a recorded call count.

WHAT MUST NOT BECOME CHEAPER IS THE CERTIFYING. One call is worth having only while it
refuses everything the four calls refused, so most of what is below is the refusals: two
sources of verification, an undeclared scope, and a red run. A single call that closed a
task the separate path would have blocked is not an optimisation, it is a hole.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import task_close_inline_verify as inline  # noqa: E402


class _Svc:
    """The service as this module uses it: a task row, an update, and a verify run."""

    def __init__(self, *, relevant_files=None, report=None):
        self._row = {"slug": "t", "relevant_files": relevant_files}
        self._report = {"status": "ok", "trigger": "verify", "results": []}
        self._report.update(report or {"passed": True, "verify_handle": "42.cafe"})
        self.updated: dict = {}
        self.ran: list = []

    def task_show(self, slug):
        return dict(self._row)

    def task_update(self, slug, **kw):
        self.updated = kw

    def run_verify_for_task(self, slug, **kw):
        self.ran.append((slug, kw))
        return dict(self._report)


def _args(**kw):
    base = {
        "slug": "t",
        "verify": True,
        "verify_handle": None,
        "relevant_files": None,
        "no_file_changes": False,
        "no_tests_expected": False,
    }
    base.update(kw)
    return SimpleNamespace(**base)


class TestTheOneCallStillCertifies:
    def test_a_green_run_hands_back_the_handle_the_close_must_present(self, monkeypatch):
        """The handle is not bypassed, it is obtained. `task done` redeems the same
        single-use identifier it would have been given by hand."""
        monkeypatch.setattr(inline, "_CLI", ".tausik/tausik")
        svc = _Svc(relevant_files='["a.py"]')
        handle = inline.handle_for_close(svc, _args(), echo=lambda _s: None)
        assert handle == "42.cafe"
        assert svc.ran and svc.ran[0][1]["trigger"] == "verify"

    def test_a_run_that_earned_no_handle_returns_empty_rather_than_inventing_one(self):
        """An unsigned receipt is a real state — no project key, a signing failure. The
        close falls back to the freshness lookup; fabricating a handle here would be the
        hidden server state the handle exists to replace."""
        svc = _Svc(relevant_files='["a.py"]', report={"passed": True, "verify_handle": None})
        assert inline.handle_for_close(svc, _args(), echo=lambda _s: None) == ""


class TestWhatTheOneCallRefuses:
    def test_a_red_run_stops_the_close_before_the_task_is_touched(self):
        """NEGATIVE, AC-3. The report is printed first: what an agent does next depends on
        WHICH gate went red, and a one-call close that swallowed it would trade four cheap
        calls for one blind one."""
        printed: list[str] = []
        svc = _Svc(relevant_files='["a.py"]', report={"passed": False, "verify_handle": None})
        with pytest.raises(SystemExit) as exc:
            inline.handle_for_close(svc, _args(), echo=printed.append)
        assert exc.value.code == 1
        assert printed, "the refusal names which gate went red"

    def test_an_undeclared_scope_is_refused_rather_than_certified_narrowly(self):
        """NEGATIVE, AC-4. A verify over an undeclared scope skips the scoped gates and
        still signs a receipt — one call that did that would be a cheaper way to certify
        nothing, which is the opposite of the point."""
        from project_service import ServiceError

        svc = _Svc(relevant_files=None)
        with pytest.raises(ServiceError) as exc:
            inline.handle_for_close(svc, _args(), echo=lambda _s: None)
        assert "--no-file-changes" in str(exc.value), "the honest way out is named"
        assert not svc.ran, "nothing was run, so nothing was recorded"

    def test_a_task_that_really_changed_no_files_says_so_and_passes(self):
        """The paired positive: `--no-file-changes` is the framework's own vocabulary for
        an empty scope, so the refusal above must not also catch it."""
        svc = _Svc(relevant_files=None)
        assert inline.handle_for_close(svc, _args(no_file_changes=True), echo=lambda _s: None)

    def test_two_sources_of_verification_in_one_call_are_refused(self):
        """NEGATIVE, AC-5. Only one run gets redeemed, and the output does not say which —
        so the caller is asked for one rather than guessed at."""
        from project_service import ServiceError

        with pytest.raises(ServiceError) as exc:
            inline.refuse_two_sources(_args(verify_handle="7.beef"))
        assert "--verify-handle" in str(exc.value) and "--verify" in str(exc.value)

    @pytest.mark.parametrize(
        ("verify", "handle"),
        [(True, None), (False, "7.beef"), (False, None)],
        ids=["only_verify", "only_handle", "neither"],
    )
    def test_one_source_or_none_is_left_alone(self, verify, handle):
        inline.refuse_two_sources(_args(verify=verify, verify_handle=handle))


class TestTheCloseGatesAnnounceThemselvesBeforeTheCeremony:
    def test_a_gate_that_will_refuse_the_close_is_reported_at_verify_time(self, monkeypatch):
        """AC-2. `changelog` runs only at `task done`, so an agent meets it after the
        ceremony has already cost a call. The REAL gate is asked — a second copy of the
        rule here would be a copy that drifts."""

        def _fake(svc, report, slug, **kw):
            report["passed"] = False
            report["blocking_failures"].append(
                {"gate": "changelog", "output": "no entry", "remediation": "add a line"}
            )

        monkeypatch.setattr("gate_changelog.enforce_changelog", _fake)
        lines = inline.post_close_advisory(_Svc(), "t")
        assert len(lines) == 1
        assert "changelog" in lines[0] and "add a line" in lines[0]
        assert "AT CLOSE, NOT NOW" in lines[0], "it must not read as a refusal of this run"

    def test_a_satisfied_gate_says_nothing(self, monkeypatch):
        monkeypatch.setattr("gate_changelog.enforce_changelog", lambda *a, **k: None)
        assert inline.post_close_advisory(_Svc(), "t") == []

    def test_an_advisory_that_raises_never_breaks_the_run_it_advises(self, monkeypatch):
        """It is an advisory. A verify that died because its footnote failed would be a
        worse trade than the four calls this replaces."""

        def _boom(*a, **k):
            raise RuntimeError("config unreadable")

        monkeypatch.setattr("gate_changelog.enforce_changelog", _boom)
        assert inline.post_close_advisory(_Svc(), "t") == []


class TestTheFlagIsReachableFromTheCommandLine:
    def test_task_done_declares_verify_and_it_defaults_off(self):
        """The default matters: every existing caller keeps the separate path unchanged."""
        import argparse

        from project_parser_task import add_task

        parser = argparse.ArgumentParser()
        add_task(parser.add_subparsers(dest="cmd"))
        args = parser.parse_args(["task", "done", "t", "--ac-verified"])
        assert args.verify is False
        args = parser.parse_args(["task", "done", "t", "--ac-verified", "--verify"])
        assert args.verify is True
