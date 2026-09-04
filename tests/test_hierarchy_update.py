"""`epic update` / `story update`, and the stale-description report they feed.

Until these existed an epic's or story's description could not be changed at
all: the commands were add, list, done, delete. The description is how a fresh
agent reads the INTENT of a group of tasks, so an unchangeable one aged into a
false standing claim — found twice in one session (#189), worked around by
keeping the intent in decisions that only help while someone reads them.

Three properties are pinned here beyond the commands working:

* ONE IMPLEMENTATION. The CLI and the MCP tool both call `hierarchy_edit`;
  neither carries logic of its own and neither reaches the backend. Asserted
  on the AST of both callers, not by reading them.
* A MODULE, NOT MORE CLASS SURFACE. `hierarchy_edit` adds nothing public to
  ProjectService or SQLiteBackend — the class-surface ratchet only turns down,
  and the first draft grew both.
* A REPORT, NOT A GATE. `stale` counts tasks created after the description was
  last edited (the `description_updated` event; with no edit ever, the group's
  own `created_at`). It names; it never blocks — done goes through at any
  number, and that is asserted too, because a description rewritten to pass a
  check is worse than one honestly old.
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_TESTS, "..", "scripts"))
_MCP = os.path.abspath(os.path.join(_TESTS, "..", "harness", "claude", "mcp", "project"))
for _p in (_SCRIPTS, _MCP):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import hierarchy_edit as HE  # noqa: E402
from handlers import handle_tool  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_parser import build_parser  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "h.db")))
    s.epic_add("e1", "Epic one", "three layers of the agent's path")
    s.story_add("e1", "s1", "Story one", "the premise")
    yield s
    s.be.close()


def _events(svc, kind, slug):
    return svc.be._q(
        "SELECT action FROM events WHERE entity_type=? AND entity_id=? ORDER BY id",
        (kind, slug),
    )


def _backdate(svc):
    svc.be._conn.execute("UPDATE epics SET created_at='2020-01-01T00:00:00Z'")
    svc.be._conn.execute("UPDATE stories SET created_at='2020-01-01T00:00:00Z'")


# --- the one implementation ---------------------------------------------------


class TestUpdate:
    def test_epic_description_and_title_change(self, svc):
        out = HE.update(svc, "epics", "e1", title="Epic one, replanned", description="four")
        assert out == "Epic 'e1' updated (description and title)."
        row = svc.be.epic_get("e1")
        assert (row["title"], row["description"]) == ("Epic one, replanned", "four")

    def test_story_description_changes_alone(self, svc):
        assert HE.update(svc, "stories", "s1", description="premise withdrawn by #267") == (
            "Story 's1' updated (description)."
        )
        assert svc.be.story_get("s1")["description"] == "premise withdrawn by #267"
        assert svc.be.story_get("s1")["title"] == "Story one"

    def test_a_description_edit_is_journaled_as_an_event(self, svc):
        HE.update(svc, "epics", "e1", description="x")
        assert [e["action"] for e in _events(svc, "epics", "e1")] == [HE.EDIT_EVENT]

    def test_a_title_only_edit_is_not_a_description_edit(self, svc):
        HE.update(svc, "epics", "e1", title="renamed")
        assert _events(svc, "epics", "e1") == []

    def test_nothing_to_update_is_refused(self, svc):
        with pytest.raises(ServiceError, match="nothing to update"):
            HE.update(svc, "epics", "e1")
        with pytest.raises(ServiceError, match="nothing to update"):
            HE.update(svc, "stories", "s1")

    def test_an_unknown_slug_fails_like_done_does(self, svc):
        with pytest.raises(ServiceError, match="Epic 'nope' not found"):
            HE.update(svc, "epics", "nope", title="x")
        with pytest.raises(ServiceError, match="Story 'nope' not found"):
            HE.update(svc, "stories", "nope", title="x")

    def test_an_overlong_title_is_refused(self, svc):
        # The same guard `epic add` raises (validate_length), the same type.
        with pytest.raises(ValueError, match="max 512"):
            HE.update(svc, "epics", "e1", title="t" * 1000)

    def test_a_multiline_description_collapses_like_add(self, svc):
        HE.update(svc, "stories", "s1", description="first line\nsecond line")
        assert "\n" not in svc.be.story_get("s1")["description"]

    @pytest.mark.parametrize("field", ["title", "description"])
    def test_an_empty_string_is_refused_and_writes_nothing(self, svc, field):
        """Blanking the description would reset `stale` — the one way to pass
        the report by destroying what it measures (review #208, record #23)."""
        with pytest.raises(ServiceError, match=f"empty {field}"):
            HE.update(svc, "epics", "e1", **{field: "   "})
        assert svc.be.epic_get("e1")[field] != "   "
        assert svc.be.epic_get("e1")[field]
        assert _events(svc, "epics", "e1") == []


# --- the callers carry no logic of their own --------------------------------


def _attr_calls(path: str, func: str | None = None) -> set[str]:
    """`<name>.<attr>(...)` call targets in module `path` (inside `func` if given)."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    scope: list[ast.AST] = [tree]
    if func is not None:
        scope = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func]
        assert scope, f"{func} not found in {path}"
    out: set[str] = set()
    for root in scope:
        for node in ast.walk(root):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                out.add(ast.unparse(node.func))
    return out


@pytest.mark.parametrize(
    ("path", "func", "expected"),
    [
        (os.path.join(_SCRIPTS, "project_cli.py"), "cmd_epic", "hierarchy_edit.update"),
        (os.path.join(_SCRIPTS, "project_cli.py"), "cmd_story", "hierarchy_edit.update"),
        (os.path.join(_MCP, "handlers_hierarchy.py"), None, "hierarchy_edit.update"),
    ],
)
def test_each_caller_calls_the_one_implementation_and_nothing_below_it(path, func, expected):
    calls = _attr_calls(path, func)
    assert expected in calls, f"{path}:{func} does not call {expected}"
    assert "hierarchy_edit.list_with_staleness" in calls
    below = {c for c in calls if ".be." in c or c.endswith(("epic_update", "story_update"))}
    assert below == set(), f"{path}:{func} reaches past the one implementation: {below}"


def test_nothing_public_was_added_to_the_god_classes():
    """The ratchet's own reason, restated where the temptation lives."""
    for name in ("epic_update", "story_update", "description_staleness", "list_with_staleness"):
        assert not hasattr(ProjectService, name)
    # The backend's own `epic_update` / `story_update` predate this change;
    # what must NOT have appeared there are the staleness queries.
    for name in ("last_event_at", "tasks_created_after"):
        assert not hasattr(SQLiteBackend, name)


class TestCallers:
    def test_mcp_update_tools_round_trip(self, svc):
        assert "updated (description)" in handle_tool(
            svc, "tausik_epic_update", {"slug": "e1", "description": "via mcp"}
        )
        assert svc.be.epic_get("e1")["description"] == "via mcp"
        assert "updated (title)" in handle_tool(
            svc, "tausik_story_update", {"slug": "s1", "title": "via mcp"}
        )
        assert svc.be.story_get("s1")["title"] == "via mcp"

    def test_mcp_tools_are_declared_for_both(self):
        from tools import TOOLS

        names = {t["name"] for t in TOOLS}
        assert {"tausik_epic_update", "tausik_story_update"} <= names

    def test_cli_parser_accepts_update_and_stale_over(self):
        p = build_parser()
        a = p.parse_args(["epic", "update", "e1", "--description", "d", "--title", "t"])
        assert (a.epic_cmd, a.slug, a.title, a.description) == ("update", "e1", "t", "d")
        a = p.parse_args(["story", "update", "s1", "--description", "d"])
        assert (a.story_cmd, a.slug, a.title, a.description) == ("update", "s1", None, "d")
        assert p.parse_args(["epic", "list", "--stale-over", "3"]).stale_over == 3
        assert p.parse_args(["story", "list"]).stale_over is None

    def test_stale_over_zero_is_a_filter_and_no_flag_is_none(self):
        """An explicit `--stale-over 0` keeps rows with stale > 0; no flag keeps all
        (review #208: `0 or 0` read the explicit zero as "no filter")."""
        from argparse import Namespace

        from project_cli import _stale_rows

        rows = [{"slug": "a", "stale": 0}, {"slug": "b", "stale": 2}]
        assert _stale_rows(rows, Namespace(stale_over=None)) == rows
        assert _stale_rows(rows, Namespace(stale_over=0)) == [rows[1]]
        assert _stale_rows(rows, Namespace(stale_over=2)) == []


# --- stale descriptions: a report, deliberately not a gate -------------------


class TestStaleness:
    def test_tasks_added_after_the_description_was_written_count(self, svc):
        _backdate(svc)
        svc.task_add("s1", "t1", "Task 1")
        svc.task_add("s1", "t2", "Task 2")
        assert HE.staleness(svc, "epics", "e1") == 2
        assert HE.staleness(svc, "stories", "s1") == 2

    def test_an_edit_resets_the_count(self, svc):
        _backdate(svc)
        svc.task_add("s1", "t1", "Task 1")
        svc.be._conn.execute("UPDATE tasks SET created_at='2021-01-01T00:00:00Z'")
        HE.update(svc, "epics", "e1", description="rewritten after t1")
        assert HE.staleness(svc, "epics", "e1") == 0
        svc.task_add("s1", "t2", "Task 2")
        svc.be._conn.execute("UPDATE tasks SET created_at='2999-01-01T00:00:00Z' WHERE slug='t2'")
        assert HE.staleness(svc, "epics", "e1") == 1

    def test_a_task_created_in_the_same_second_as_the_edit_is_not_counted(self, svc):
        """The boundary, pinned: strict `>` (review #208 found `>=` survived)."""
        _backdate(svc)
        svc.task_add("s1", "t1", "Task 1")
        HE.update(svc, "epics", "e1", description="rewritten")
        at = svc.be._q1(
            "SELECT created_at AS at FROM events WHERE entity_type='epics' AND entity_id='e1'"
        )["at"]
        svc.be._conn.execute("UPDATE tasks SET created_at=? WHERE slug='t1'", (at,))
        assert HE.staleness(svc, "epics", "e1") == 0
        svc.be._conn.execute("UPDATE tasks SET created_at='2999-01-01T00:00:00Z' WHERE slug='t1'")
        assert HE.staleness(svc, "epics", "e1") == 1

    def test_a_title_edit_does_not_reset_the_count(self, svc):
        _backdate(svc)
        svc.task_add("s1", "t1", "Task 1")
        HE.update(svc, "epics", "e1", title="renamed only")
        assert HE.staleness(svc, "epics", "e1") == 1

    def test_the_lists_carry_the_number(self, svc):
        _backdate(svc)
        svc.task_add("s1", "t1", "Task 1")
        assert HE.list_with_staleness(svc, "epics")[0]["stale"] == 1
        assert HE.list_with_staleness(svc, "stories", "e1")[0]["stale"] == 1
        assert "(stale: 1)" in handle_tool(svc, "tausik_epic_list", {})
        assert "(stale: 1)" in handle_tool(svc, "tausik_story_list", {})

    def test_a_fresh_group_is_not_stale(self, svc):
        assert HE.list_with_staleness(svc, "epics")[0]["stale"] == 0
        assert "stale" not in handle_tool(svc, "tausik_epic_list", {})

    def test_stale_never_blocks_closing(self, svc):
        """The negative scenario of the task, literally: not a gate."""
        _backdate(svc)
        for i in range(25):
            svc.task_add("s1", f"t{i}", f"Task {i}")
        assert HE.staleness(svc, "epics", "e1") == 25
        for i in range(25):
            svc.be.task_update(f"t{i}", status="done")
        assert svc.story_done("s1") == "Story 's1' marked done."
        assert svc.epic_done("e1") == "Epic 'e1' marked done."
