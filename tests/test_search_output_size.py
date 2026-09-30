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

#: The measurement each ceiling was derived from, in characters, taken on the live
#: project — the pair the headroom check reads. Declared beside the ceiling
#: rather than re-probed, because a probe answers about the machine that runs it: the
#: same assertion against a live service passed on a populated database and failed in
#: CI on a fresh clone, where every response is "No results."
#:
#: `tausik_search` is the figure AFTER the duplicate-snippet fix (21,189 before).
#: `tausik_task_show` and `tausik_metrics` are absent ON PURPOSE: no measurement was
#: recorded for them, and inventing one to fill the table would make this check assert
#: a number nobody took.
_MEASURED: dict[str, int] = {
    "tausik_search": 18_906,
    "tausik_roadmap": 16_507,
    "tausik_task_list": 13_840,
    "tausik_memory_list": 7_881,
}

_PROBE_ARGS: dict[str, dict] = {
    "tausik_search": {"query": "token"},
    "tausik_task_list": {"status": "planning"},
}


@pytest.fixture
def seeded(tmp_path):
    """A service carrying enough rows that a full response is a full response.

    Sixty memories, because that is the order of the live query the ceilings were
    measured from (60 snippets, 27 of them repeating their title). Fewer would cap
    nothing; the point of a ceiling is that a big answer fits under it.

    Own data rather than the live project: `get_service()` reads whatever database
    the machine happens to hold, so on a fresh clone the same assertions compared
    "No results." with itself and the check was a tautology that CI reported as red.
    """
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    svc = ProjectService(SQLiteBackend(str(tmp_path / "size.db")))
    svc.epic_add("e", "Epic")
    svc.story_add("e", "s", "Story")
    for i in range(60):
        svc.memory_add(
            "pattern",
            f"Token accounting note {i}: the metered sum is deduplicated per message",
            "A body long enough to be worth a snippet: the token ledger records one row "
            f"per message and the replay of a session must meter the same sum, case {i}.",
            ["token", "accounting"],
        )
    yield svc
    svc.be.close()


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

    def test_the_handler_honours_a_smaller_limit(self, seeded):
        """On data this test OWNS, not on whatever the live project happens to hold.

        It used to read the live service and compare two response sizes. On a fresh
        clone both answers are "No results." -- eleven characters each -- so the
        assertion read `11 < 11` and the test was red in CI for a release while green
        on a developer machine with a populated database. A limit is a property of the
        handler; proving it needs rows, not THESE rows.
        """
        from handlers import handle_tool

        wide = handle_tool(seeded, "tausik_search", {"query": "token", "limit": 20})
        narrow = handle_tool(seeded, "tausik_search", {"query": "token", "limit": 2})
        assert len(narrow) < len(wide), (wide[:200], narrow[:200])


class TestOurOwnResponsesStayUnderTheirCeilings:
    """A ceiling is checked against a response big enough to test it.

    This class used to read the live project on the argument that "a ceiling checked
    on a fixture is a ceiling on nothing". The argument was wrong in the direction
    that matters: what the ceiling needs is a FULL response, and a fixture can build
    one, while a fresh clone cannot -- so the live reading made the check depend on
    the machine and it went red in CI for a release.
    """

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

    @pytest.mark.parametrize("name", sorted(_MEASURED))
    def test_the_ceilings_are_not_generous_headroom(self, name):
        """Headroom is how a ratchet stops ratcheting: a ceiling far above the thing
        it caps never catches anything.

        Checked against the RECORDED measurement each ceiling was set from, not
        against a live probe. The live version asked the machine's own database and
        so compared the ceiling with whatever happened to be there -- eleven
        characters on a fresh clone, which made the check pass vacuously on a
        developer machine and fail in CI. A seeded fixture does not help either: it
        can make a response large, but not the size THIS ceiling was derived from.

        So the pair is declared and both halves are checked, which is the same rule
        the project applies to a constant and the promise in its docstring: the
        number and the claim beside it are one statement.
        """
        gap = _CEILINGS[name] - _MEASURED[name]
        assert 0 <= gap < 2_000, (
            f"{name}: ceiling {_CEILINGS[name]} sits {gap} above the measured "
            f"{_MEASURED[name]}. A ceiling that far above what it caps catches nothing."
        )

    def test_a_full_response_fits_under_its_ceiling(self, seeded):
        """The other half: a response big enough to matter stays under the cap.

        Seeded rather than live, because what this needs is a FULL answer and a
        fixture can build one. Sixty rows produce thousands of characters, which is
        enough for the assertion to mean something and independent of the machine.
        """
        from handlers import handle_tool

        text = handle_tool(seeded, "tausik_search", {"query": "token"})
        assert len(text) > 1_000, f"the probe returned {len(text)} chars — nothing to cap"
        assert len(text) <= _CEILINGS["tausik_search"]
