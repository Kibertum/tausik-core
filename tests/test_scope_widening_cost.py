"""Widening a declared scope costs one short call, and still cannot happen by accident.

THE MEASUREMENT. A task's scope is declared BEFORE the work reveals which files it touches,
so the ACL refuses in almost every non-trivial task — seven refusals across three
consecutive tasks in the session that filed this, the last on the module that fixes it,
which could not have been named in a declaration written before it existed. Each refusal
cost two calls: the refusal, then a `task update --scope-paths` restating the WHOLE list.

WHAT MUST NOT GET CHEAPER IS THE DECLARING. Rule 2 says the agent names what it may write.
So the tests below are mostly about what widening still refuses: an ambiguous pair of
flags, an empty list that would revoke rather than widen, and a duplicate that would make
the declared list grow without saying anything new.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (_REPO / "scripts", _REPO / "scripts" / "hooks"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import task_scope_widen as widen_mod  # noqa: E402


class _Svc:
    def __init__(self, scope_paths=None):
        self._row = {"slug": "t", "scope_paths": scope_paths}
        self.updated: dict = {}

    def task_show(self, slug):
        return dict(self._row)

    def task_update(self, slug, **kw):
        self.updated = kw
        return "ok"


class TestWideningKeepsWhatWasThere:
    @pytest.mark.parametrize(
        "stored",
        [
            pytest.param('["a.py", "b.py"]', id="stored_as_json"),
            pytest.param(["a.py", "b.py"], id="stored_as_a_list"),
        ],
    )
    def test_the_declared_paths_survive_the_addition(self, stored):
        """Both shapes are read because the row has carried both; a reader that knew only
        one would silently see an empty scope and widen from nothing."""
        svc = _Svc(stored)
        said = widen_mod.widen(svc, "t", ["c.py"])
        assert svc.updated["scope_paths"] == ["a.py", "b.py", "c.py"]
        assert "c.py" in said and "3 total" in said

    def test_a_task_that_declared_nothing_can_still_be_widened(self):
        svc = _Svc(None)
        widen_mod.widen(svc, "t", ["a.py"])
        assert svc.updated["scope_paths"] == ["a.py"]

    def test_a_path_already_declared_is_not_added_twice_and_is_said_so(self):
        """AC-5. Appending it again would grow the list on every retry and make the ACL
        unreadable — and the caller who typed it deserves to know it was already allowed."""
        svc = _Svc('["a.py"]')
        said = widen_mod.widen(svc, "t", ["a.py"])
        assert svc.updated == {}, "nothing was written"
        assert "already declared" in said.lower()

    def test_a_mixed_call_adds_only_what_is_new_and_names_both_halves(self):
        svc = _Svc('["a.py"]')
        said = widen_mod.widen(svc, "t", ["a.py", "b.py"])
        assert svc.updated["scope_paths"] == ["a.py", "b.py"]
        assert "b.py" in said and "a.py" in said


class TestWhatWideningRefuses:
    def test_an_empty_list_is_refused_rather_than_read_as_a_revocation(self):
        """NEGATIVE, AC-4. An empty list is almost always a shell glob that matched
        nothing; clearing a declared ACL on one would turn a widening into a total
        revocation, and the next write would be allowed nowhere."""
        from project_service import ServiceError

        svc = _Svc('["a.py"]')
        with pytest.raises(ServiceError) as exc:
            widen_mod.widen(svc, "t", [])
        assert "--scope-paths" in str(exc.value), "the deliberate way to clear it is named"
        assert svc.updated == {}

    def test_replacing_and_adding_in_one_command_is_refused(self):
        """NEGATIVE, AC-3. Which flag won would not be visible in the output, and an ACL
        the caller cannot read back is one they stop trusting."""
        from project_service import ServiceError

        args = SimpleNamespace(scope_paths=["a.py"], add_scope_paths=["b.py"])
        with pytest.raises(ServiceError) as exc:
            widen_mod.refuse_conflicting_flags(args)
        assert "--scope-paths" in str(exc.value) and "--add-scope-paths" in str(exc.value)

    @pytest.mark.parametrize(
        ("scope_paths", "add_scope_paths"),
        [(["a.py"], None), (None, ["b.py"]), (None, None), ([], None)],
        ids=["only_replace", "only_add", "neither", "explicit_empty_replace"],
    )
    def test_one_flag_or_none_is_left_alone(self, scope_paths, add_scope_paths):
        widen_mod.refuse_conflicting_flags(
            SimpleNamespace(scope_paths=scope_paths, add_scope_paths=add_scope_paths)
        )


class TestTheRefusalPrintsTheCheapCommand:
    def test_it_names_only_the_blocked_paths_and_the_additive_flag(self):
        """AC-2. The old text said `--scope-paths <existing...> <path>`: it asked the
        reader to retype the declared list, which is the expensive half of the two calls
        and the half where a path goes missing."""
        cmd = widen_mod.widen_command("t", ["scripts/x.py", "scripts/y.py"])
        assert "--add-scope-paths" in cmd
        assert "<existing" not in cmd, "nothing has to be restated"
        assert cmd.endswith("scripts/x.py scripts/y.py"), "sorted, so two runs agree"

    def test_a_repeated_path_is_named_once(self):
        """A Bash command can name the same file twice; the refusal should not."""
        assert widen_mod.widen_command("t", ["a.py", "a.py"]).count("a.py") == 1

    @pytest.mark.parametrize(
        "module", ["scope_write_gate", "bash_write_gate"], ids=["write_tool", "bash"]
    )
    def test_both_hooks_build_their_refusal_from_that_one_command(self, module):
        """Two hooks enforce the same rule, and their texts had drifted apart before.
        Reading the source keeps this honest without launching a host."""
        text = (_REPO / "scripts" / "hooks" / f"{module}.py").read_text(encoding="utf-8")
        assert "widen_command(" in text
        assert "--scope-paths <existing" not in text, "the restating form is gone"


class TestTheFlagIsReachableFromTheCommandLine:
    def test_task_update_declares_add_scope_paths(self):
        import argparse

        from project_parser_task import add_task

        parser = argparse.ArgumentParser()
        add_task(parser.add_subparsers(dest="cmd"))
        args = parser.parse_args(["task", "update", "t", "--add-scope-paths", "a.py", "b.py"])
        assert args.add_scope_paths == ["a.py", "b.py"]
        assert args.scope_paths is None, "adding must not look like replacing"

    def test_the_stored_value_round_trips_as_a_list(self):
        """The row is read back by the hooks, so what widen writes has to be what
        `--scope-paths` writes — otherwise the ACL means one thing per code path."""
        svc = _Svc('["a.py"]')
        widen_mod.widen(svc, "t", ["b.py"])
        stored = svc.updated["scope_paths"]
        assert json.loads(json.dumps(stored)) == ["a.py", "b.py"]
