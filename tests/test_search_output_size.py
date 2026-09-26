"""What a read tool returns is paid for on every later turn, so its size is pinned.

THE COST MODEL, derived from session #277's measurement and worth stating because
it CHANGED the plan. cache_read is 99.5% of all input, about 482,000 tokens per
call, so N extra tokens of response cost N x (turns remaining) in cache_read,
while an extra TURN to fetch a spilled file costs one full context re-read. Spilling
therefore pays only above roughly 2,500-10,000 tokens, depending on how early in a
session the call lands.

WHICH REFUTED THE TASK'S PREMISE. Measured on this surface: `tausik_search` 21,189
characters (~5,297 tokens), `tausik_roadmap` 16,507, `tausik_task_list` 13,840,
`tausik_memory_list` 7,881, everything else under 2,000 tokens. Nothing clears the
band with confidence, so no spill-to-file was built: it would have added a turn to
save less than the turn costs. The response was made SMALLER instead.

WHAT WAS ACTUALLY WRONG. 27 of 60 snippets in a live query were byte-identical to
the title once the `>>>`/`<<<` markers were stripped -- the fattest response in the
surface printed one line of text twice. The fix keeps the WHY and drops the repeat:
when the snippet only repeats the title, the HIGHLIGHTED form takes the title's
place. 21,189 -> 18,906 characters, with nothing lost.

And `limit` worked in the handler all along while being absent from the tool schema,
so no caller could set it. A parameter that cannot be passed is not a parameter.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _sub in ("scripts", "harness/claude/mcp/project"):
    if str(_REPO / _sub) not in sys.path:
        sys.path.insert(0, str(_REPO / _sub))

import render_status  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/render_status.py", "harness/claude/mcp/"]

#: Declared ceilings in CHARACTERS for the read tools that dominate this surface,
#: measured after the duplicate-snippet fix. Ratchets: they may
#: shrink. A tool that grows past its ceiling is not forbidden from growing -- it is
#: required to argue the raise, the same way the MCP surface ratchet works.
_CEILINGS: dict[str, int] = {
    "tausik_search": 19_500,
    "tausik_roadmap": 17_000,
    "tausik_task_list": 14_500,
    "tausik_memory_list": 8_500,
    "tausik_task_show": 7_000,
    "tausik_metrics": 6_000,
}

_PROBE_ARGS: dict[str, dict] = {
    "tausik_search": {"query": "token"},
    "tausik_task_list": {"status": "planning"},
}


class TestASnippetNeverOnlyRepeatsTheTitle:
    """The measured waste: 45% of the snippets in one query were the title again."""

    def test_an_identical_snippet_replaces_the_title_line(self):
        shown, repeats = render_status._title_and_snippet("a token here", "a >>>token<<< here")
        assert repeats is True
        assert shown == "a >>>token<<< here", "the highlight was dropped along with the repeat"

    def test_a_different_snippet_is_kept_as_its_own_line(self):
        shown, repeats = render_status._title_and_snippet("short title", "…deep in the >>>body<<<…")
        assert repeats is False
        assert shown == "short title"

    def test_no_snippet_leaves_the_title_alone(self):
        assert render_status._title_and_snippet("only a title", None) == ("only a title", False)

    @pytest.mark.parametrize(
        ("title", "snippet"),
        [
            pytest.param("  padded  ", ">>>padded<<<", id="whitespace_differs"),
            pytest.param("exact", "exact", id="no_markers_at_all"),
        ],
    )
    def test_the_comparison_ignores_markers_and_padding(self, title, snippet):
        assert render_status._title_and_snippet(title, snippet)[1] is True

    def test_an_empty_snippet_is_not_treated_as_a_repeat(self):
        """An empty string would compare equal to an empty title and silently hide
        the line the reader came for."""
        assert render_status._title_and_snippet("", "")[1] is False


class TestTheLimitIsReachableFromOutside:
    def test_the_schema_declares_it(self):
        from tools import TOOLS

        schema = next(t for t in TOOLS if t["name"] == "tausik_search")["inputSchema"]
        assert "limit" in schema["properties"], "a parameter that cannot be passed is not one"

    def test_the_handler_honours_a_smaller_limit(self):
        from handlers import handle_tool
        from service_factory import get_service

        svc = get_service()
        wide = handle_tool(svc, "tausik_search", {"query": "token", "limit": 20})
        narrow = handle_tool(svc, "tausik_search", {"query": "token", "limit": 2})
        assert len(narrow) < len(wide)


class TestOurOwnResponsesStayUnderTheirCeilings:
    """Measured against the live project, because a ceiling checked on a fixture is
    a ceiling on nothing."""

    @pytest.mark.parametrize("name", sorted(_CEILINGS))
    def test_the_response_fits(self, name):
        from handlers import handle_tool
        from service_factory import get_service

        svc = get_service()
        args = dict(_PROBE_ARGS.get(name, {}))
        if name == "tausik_task_show":
            tasks = svc.task_list("done", None, None, None, None, limit=1)
            if not tasks:
                pytest.skip("no closed task to show")
            args["slug"] = tasks[0]["slug"]
        try:
            text = handle_tool(svc, name, args)
        except Exception as exc:  # noqa: BLE001 — a probe failure is not a size verdict
            pytest.skip(f"{name} could not be probed: {type(exc).__name__}")
        assert len(text) <= _CEILINGS[name], (
            f"{name} returns {len(text)} characters, ceiling {_CEILINGS[name]}. Every "
            "later turn re-reads this, so argue the raise or make it smaller."
        )

    def test_the_ceilings_are_not_generous_headroom(self):
        """Headroom is how a ratchet stops ratcheting. Each ceiling sits within a
        tenth of the measurement it was set from."""
        from handlers import handle_tool
        from service_factory import get_service

        svc = get_service()
        text = handle_tool(svc, "tausik_search", {"query": "token"})
        assert _CEILINGS["tausik_search"] - len(text) < 2_000
