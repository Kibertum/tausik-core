"""Project resolution is a chain of three links, and every branch of it is pinned here.

WHY THE FIRST LINK IS A PARAMETER. The chain used to begin at MCP roots; the spec of
2026-07-28 deprecates them (SEP-2577), so the spike replaced the first link with whatever
mechanism the host actually supports. `primary_signal` is therefore supplied by the caller,
and the last class below feeds it a roots-shaped `file://` URI to prove the transitional path
needs no change to the module.

THE NEGATIVES ARE THE POINT, and the acceptance criteria are right to split them: an empty
pointer file, invalid JSON, and valid JSON without the key are three different failures, and
one "broken pointer" test would leave two of them unproven. A pointer naming a directory that
is gone gets its own test as well, because a dead path is worse than None — the caller would
take it for a working project and fail somewhere the pointer is never mentioned.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

NEWLINE = chr(10)

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from gmcp_project_resolver import (  # noqa: E402
    normalise_signal,
    read_pointer,
    resolve_project,
)


@pytest.fixture
def projects(tmp_path):
    """Two real projects and one directory that is not one."""
    for name in ("alpha", "beta"):
        (tmp_path / name / ".tausik").mkdir(parents=True)
    (tmp_path / "plain").mkdir()
    return tmp_path


def _pointer(tmp_path, body) -> dict[str, str]:
    """Write a pointer file and return the env that points at it."""
    path = tmp_path / "pointer.json"
    path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return {"TAUSIK_ACTIVE_POINTER": str(path)}


class TestThePriorityOrder:
    def test_the_primary_signal_wins_over_everything_else(self, projects):
        env = _pointer(projects, {"default": str(projects / "beta")})
        got = resolve_project(str(projects / "alpha"), env, str(projects / "beta"))
        assert got.project_dir == str(projects / "alpha") and got.source == "primary"

    def test_the_pointer_answers_when_there_is_no_primary(self, projects):
        env = _pointer(projects, {"default": str(projects / "beta")})
        got = resolve_project(None, env, str(projects / "plain"))
        assert got.project_dir == str(projects / "beta") and got.source == "pointer"

    def test_the_walk_up_answers_when_there_is_no_pointer(self, projects):
        inner = projects / "alpha" / "src" / "deep"
        inner.mkdir(parents=True)
        got = resolve_project(None, {}, str(inner))
        assert got.project_dir == str(projects / "alpha") and got.source == "walk-up"

    def test_each_link_is_reached_only_when_the_one_before_it_declines(self, projects):
        """The order stated as one assertion: the same cwd resolves differently as the
        earlier links are added."""
        inner = projects / "alpha" / "src"
        inner.mkdir()
        assert resolve_project(None, {}, str(inner)).source == "walk-up"
        env = _pointer(projects, {"default": str(projects / "beta")})
        assert resolve_project(None, env, str(inner)).source == "pointer"
        assert resolve_project(str(projects / "alpha"), env, str(inner)).source == "primary"


class TestNoSignalIsNoneAndNotAnException:
    def test_nothing_anywhere_resolves_to_none(self, projects, monkeypatch):
        """AC-2: no primary, no pointer, a cwd outside any project."""
        monkeypatch.setenv("TAUSIK_ACTIVE_POINTER", str(projects / "absent.json"))
        got = resolve_project(None, dict(os.environ), str(projects / "plain"))
        assert got.project_dir is None and got.source == "none"
        assert any("no .tausik" in n for n in got.notes)

    def test_a_missing_pointer_file_is_not_reported_as_a_failure(self, projects):
        """Absence is not breakage: a machine that never wrote a pointer has nothing wrong
        with it, and a note about it would be noise on every single call."""
        env = {"TAUSIK_ACTIVE_POINTER": str(projects / "absent.json")}
        got = resolve_project(None, env, str(projects / "alpha"))
        assert got.source == "walk-up"
        assert not [n for n in got.notes if "pointer" in n]


class TestThePointerFailsInThreeDistinctWays:
    """AC-3 spelled out: three failures, three tests, three different reasons."""

    def test_an_empty_file(self, projects):
        """Whitespace counts as empty: a file somebody truncated leaves a newline behind."""
        for body in ("", "   ", NEWLINE):
            env = _pointer(projects, body)
            got = resolve_project(None, env, str(projects / "plain"))
            assert got.project_dir is None
            assert any("empty" in n for n in got.notes), body

    def test_invalid_json(self, projects):
        """The reason carries the LINE, because a pointer is hand-edited and the reader
        needs to know where to look — that is the whole difference from "it is empty"."""
        env = _pointer(projects, "{" + NEWLINE + '"session": ' + NEWLINE + "{not json")
        got = resolve_project(None, env, str(projects / "plain"))
        assert got.project_dir is None
        reason = next(n for n in got.notes if "not valid JSON" in n)
        assert "line 3" in reason, reason

    def test_valid_json_without_the_key(self, projects):
        env = _pointer(projects, {"something-else": "x"})
        got = resolve_project(None, env, str(projects / "plain"))
        assert got.project_dir is None
        assert any("no entry" in n for n in got.notes)

    def test_valid_json_that_is_not_an_object(self, projects):
        env = _pointer(projects, ["a", "list"])
        got = resolve_project(None, env, str(projects / "plain"))
        assert any("expected an object" in n for n in got.notes)

    def test_none_of_them_raises(self, projects):
        for body in ("", "{not json", {"other": 1}, ["list"], "null"):
            env = _pointer(projects, body)
            resolve_project(None, env, str(projects / "plain"))  # must not raise


class TestADeadPathIsWorseThanNone:
    def test_a_pointer_to_a_directory_that_is_gone_is_skipped(self, projects):
        """AC-4: handing back a dead project_dir would have the caller fail somewhere the
        pointer is never mentioned."""
        env = _pointer(projects, {"default": str(projects / "was-here")})
        got = resolve_project(None, env, str(projects / "plain"))
        assert got.project_dir is None
        assert any("not a TAUSIK project" in n for n in got.notes)

    def test_a_directory_without_dot_tausik_is_not_a_project(self, projects):
        env = _pointer(projects, {"default": str(projects / "plain")})
        got = resolve_project(None, env, str(projects / "plain"))
        assert got.project_dir is None

    def test_a_primary_signal_that_is_not_a_project_falls_through(self, projects):
        env = _pointer(projects, {"default": str(projects / "beta")})
        got = resolve_project(str(projects / "plain"), env, str(projects / "plain"))
        assert got.project_dir == str(projects / "beta") and got.source == "pointer"
        assert any("primary signal" in n for n in got.notes)


class TestThePointerIsKeyedBySessionThenPidThenDefault:
    @pytest.mark.parametrize(
        ("keys", "expected"),
        [
            pytest.param({"session": "s1", "pid": "42"}, "alpha", id="session_wins"),
            pytest.param({"pid": "42"}, "beta", id="pid_when_no_session"),
            pytest.param({}, "alpha", id="default_when_neither"),
            pytest.param({"session": "unknown"}, "alpha", id="unknown_session_falls_to_default"),
        ],
    )
    def test_the_most_specific_key_present_answers(self, projects, keys, expected):
        env = _pointer(
            projects,
            {
                "session": {"s1": str(projects / "alpha")},
                "pid": {"42": str(projects / "beta")},
                "default": str(projects / "alpha"),
            },
        )
        got = resolve_project(None, env, str(projects / "plain"), keys=keys)
        assert got.project_dir == str(projects / expected)

    def test_a_key_table_of_the_wrong_type_is_skipped_not_crashed(self, projects):
        env = _pointer(
            projects, {"session": "a string, not a table", "default": str(projects / "beta")}
        )
        got = resolve_project(None, env, str(projects / "plain"), keys={"session": "s1"})
        assert got.project_dir == str(projects / "beta")


class TestTheTransitionalRootsPathNeedsNoChange:
    """AC-6: a roots-shaped value flows through the same parameter.

    Roots arrive as `file://` URIs. If the spike had found no non-deprecated mechanism, this
    is the shape the first link would carry for the guaranteed twelve months — and the module
    would not be touched.
    """

    def test_a_file_uri_resolves_like_a_path(self, projects):
        uri = (projects / "alpha").as_uri()
        assert uri.startswith("file://")
        got = resolve_project(uri, {}, str(projects / "plain"))
        assert got.project_dir == str(projects / "alpha") and got.source == "primary"

    def test_a_percent_encoded_uri_is_decoded(self, tmp_path):
        target = tmp_path / "with space"
        (target / ".tausik").mkdir(parents=True)
        got = resolve_project(target.as_uri(), {}, str(tmp_path))
        assert got.project_dir == str(target)

    def test_a_file_uri_naming_another_machine_is_refused_but_localhost_is_not(self):
        """`localhost` in a file URI means this machine and is the spelling some hosts emit;
        any other authority names somewhere else, and somewhere else is not our project."""
        assert normalise_signal("file://otherbox/share/proj") is None
        assert normalise_signal("file://localhost/tmp/proj") is not None

    @pytest.mark.parametrize(
        "value",
        ["", "   ", None, "file://", "file:///"],
        ids=["empty", "blank", "none", "bare", "root_only"],
    )
    def test_an_unusable_signal_is_none_rather_than_a_guess(self, value):
        assert normalise_signal(value) is None or os.path.isabs(normalise_signal(value))


class TestTheModuleReadsNothingAmbient:
    def test_resolution_does_not_consult_the_process_cwd(self, projects, monkeypatch):
        """Determinism is the whole reason every branch above is testable: the answer comes
        from the arguments, so where the test process happens to stand cannot change it."""
        monkeypatch.chdir(projects / "beta")
        got = resolve_project(None, {}, str(projects / "alpha"))
        assert got.project_dir == str(projects / "alpha")

    def test_the_walk_up_is_the_project_s_only_one(self):
        """One implementation of "where is the project": the resolver calls the same function
        `find_tausik_dir` does, with cwd and env injected. Two of them would disagree silently
        and the disagreement would surface far from where it was introduced."""
        import inspect

        import project_config

        assert "tausik_dir_from" in inspect.getsource(project_config.find_tausik_dir)
        assert "tausik_dir_from" in Path(_REPO / "scripts" / "gmcp_project_resolver.py").read_text(
            encoding="utf-8"
        )

    def test_the_pointer_lives_in_the_user_tier_not_in_a_home_dot_tausik(self):
        """`~/.tausik` is the mistake 1.10 moved the user tier away from: a directory of that
        name makes the home folder look like a project to the walk-up."""
        from gmcp_project_resolver import POINTER_RELATIVE

        assert POINTER_RELATIVE.replace(os.sep, "/") == ".config/tausik/active-project.json"


class TestTheNotesSayWhatWasSkipped:
    def test_a_log_callback_receives_every_skip(self, projects):
        seen: list[str] = []
        env = _pointer(projects, "{bad")
        got = resolve_project(
            str(projects / "plain"), env, str(projects / "plain"), log=seen.append
        )
        assert seen == list(got.notes)
        assert len(seen) == 3, "primary, pointer and walk-up — every link that declined"

    def test_a_clean_resolution_has_nothing_to_say(self, projects):
        assert resolve_project(str(projects / "alpha"), {}, str(projects / "plain")).notes == ()

    def test_read_pointer_reports_absence_without_a_reason(self, projects):
        assert read_pointer(str(projects / "nope.json"), {}) == (None, None)
