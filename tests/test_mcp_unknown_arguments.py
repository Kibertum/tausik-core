"""mcp-server-drops-unknown-arguments-silently — an undeclared argument is refused.

The defect these tests stand against was not hypothetical and its price was
already paid. `tausik_task_add` declares `story_slug`; it was called with
`story`. The call SUCCEEDED and returned a task, the story silently absent —
seven tasks of the artifact-graph epic went in that way, invisible to roadmap,
and the release count read them as missing. A typo in a parameter name looked
exactly like success. The CLI answered the same slip with a loud refusal listing
its options, so the two surfaces disagreed about whether it was an error at all.

What is asserted here, and what deliberately is not:

  * UNDECLARED names only. Values of DECLARED arguments already refuse loudly
    below (session #182 measured it: a 70-character slug against a limit of 64
    is named and answered with usage). Re-checking them here would duplicate a
    working check in a second place, and the second copy is what drifts.
  * The refusal must come BEFORE the handler. After it, the write has happened
    and there is nothing left to refuse — so `test_guard_runs_before_the_handler`
    reads the real dispatcher and asserts the ORDER, not merely the presence.
  * Both directions. A guard proved only on bad input is indistinguishable from
    one that refuses everything, so every refusal here is paired with the same
    tool accepting its legitimate call.

Every case runs against the REAL `TOOLS` list, not a fixture of it — a fixture
would keep passing after the production schema drifted away from it.
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
_MCP_PROJECT = os.path.join(_REPO_ROOT, "harness", "claude", "mcp", "project")
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
sys.path.insert(0, _MCP_PROJECT)

_SERVER_PATH = os.path.normpath(os.path.join(_MCP_PROJECT, "server.py"))


def _load_server():
    """Import server.py as a module. Importing does not start the server."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("tausik_mcp_server_under_test", _SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


srv = _load_server()

from tools import TOOLS  # noqa: E402 — sys.path must be set first


def _refusal(name: str, arguments: dict) -> str:
    """The text the agent would see, or fail the test if the call was accepted.

    Failing on ACCEPTANCE is the point: this suite has to redden on swallowing,
    which is the behavior being removed, not on some incidental error.
    """
    try:
        srv.reject_unknown_arguments(TOOLS, name, arguments)
    except ValueError as e:
        return srv._error_reply(TOOLS, name, e)
    pytest.fail(f"{name} accepted undeclared arguments {sorted(arguments)} — swallowing is back")


def _declared_properties(name: str) -> dict:
    declared = srv.declared_arguments(TOOLS, name)
    assert declared is not None, f"{name} is not in TOOLS"
    return declared[0]


# ---------------------------------------------------------------------------
# AC1/AC2 — the refusal names the offending key, and the name it probably meant
# ---------------------------------------------------------------------------


def test_the_live_case_that_created_the_orphans_is_now_refused():
    """`story` for `story_slug` — the exact call that cost seven tasks."""
    reply = _refusal("tausik_task_add", {"slug": "s", "title": "T", "story": "some-epic"})
    assert "'story'" in reply, reply
    assert "'story_slug'" in reply, reply
    # And the suggestion is not a coincidence of wording: story_slug is what the
    # schema actually declares, read back from the schema rather than retyped.
    assert "story_slug" in _declared_properties("tausik_task_add")


def test_the_second_live_case_task_start_swallowing_acceptance_criteria():
    """task_start takes only `slug`; QG-0 below happened to catch the loss.

    That accident is the whole shape of the defect: the silence was visible only
    where a check downstream happened to exist. task_add had none, and paid.
    """
    reply = _refusal("tausik_task_start", {"slug": "x", "acceptance_criteria": "AC1..."})
    assert "'acceptance_criteria'" in reply, reply


def test_refusal_without_a_near_name_still_lists_what_is_declared():
    """No close match to suggest is not a licence to say nothing useful."""
    reply = _refusal("tausik_task_show", {"slug": "x", "zzzz_nothing_like_it": 1})
    assert "'zzzz_nothing_like_it'" in reply, reply
    assert "did you mean" not in reply, reply
    # The declared names arrive via the usage line — taken FROM the product, not
    # transcribed here, so a change of wording moves the expectation with it.
    assert srv._usage_hint(TOOLS, "tausik_task_show") in reply


def test_a_tool_that_declares_no_arguments_says_so():
    zero = [t["name"] for t in TOOLS if not _declared_properties(t["name"])]
    assert zero, "expected at least one zero-argument tool in TOOLS"
    reply = _refusal(zero[0], {"slug": "x"})
    assert "'slug'" in reply, reply
    assert "declares no arguments" in reply, reply


def test_every_unknown_key_is_named_not_just_the_first():
    reply = _refusal("tausik_task_show", {"aaa_unrelated": 1, "bbb_unrelated": 2})
    assert "'aaa_unrelated'" in reply and "'bbb_unrelated'" in reply, reply


# ---------------------------------------------------------------------------
# AC3 (other half) / AC5 — legitimate calls are not touched
# ---------------------------------------------------------------------------


def test_the_same_tools_accept_their_legitimate_calls():
    """The paired half. Without it, a guard that refuses everything passes above."""
    srv.reject_unknown_arguments(TOOLS, "tausik_task_add", {"slug": "s", "title": "T"})
    srv.reject_unknown_arguments(TOOLS, "tausik_task_add", {"slug": "s", "story_slug": "e"})
    srv.reject_unknown_arguments(TOOLS, "tausik_task_start", {"slug": "x"})
    srv.reject_unknown_arguments(TOOLS, "tausik_task_show", {"slug": "x"})


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t["name"])
def test_no_declared_argument_of_any_tool_is_called_undeclared(tool):
    """AC5 over the WHOLE surface, not a sample of it.

    Every tool called with exactly the full set of names its own schema declares
    must pass. A sample would leave the one drifted tool to be found in
    production, which is where this defect was found the first time.
    """
    name = tool["name"]
    srv.reject_unknown_arguments(TOOLS, name, dict.fromkeys(_declared_properties(name), "v"))


def test_empty_and_absent_arguments_are_not_an_error():
    srv.reject_unknown_arguments(TOOLS, "tausik_task_show", {})
    srv.reject_unknown_arguments(TOOLS, "tausik_task_show", None)


def test_an_unknown_tool_is_not_answered_with_an_argument_complaint():
    """Naming the wrong problem is its own defect.

    An unknown tool is the dispatcher's refusal to make. Answering it here with
    "does not declare 'x'" would send the agent to fix a parameter name in a call
    whose real fault is the tool name.
    """
    srv.reject_unknown_arguments(TOOLS, "tausik_no_such_tool_exists", {"anything": 1})
    assert srv.declared_arguments(TOOLS, "tausik_no_such_tool_exists") is None


# ---------------------------------------------------------------------------
# AC4 — the check is derived from inputSchema, not from a second list of names
# ---------------------------------------------------------------------------


def test_a_name_becomes_legal_by_editing_the_schema_alone():
    """Mutation proof. Declaring a property is the ONLY act needed to allow it.

    If the guard carried its own list of names, this test would still be red
    after the schema changed — which is precisely the divergence AC4 forbids.
    """
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    tools = [{"name": "t", "inputSchema": schema}]

    with pytest.raises(ValueError):
        srv.reject_unknown_arguments(tools, "t", {"b": 1})

    schema["properties"]["b"] = {"type": "integer"}
    srv.reject_unknown_arguments(tools, "t", {"b": 1})  # no edit to the guard


def test_the_usage_line_and_the_guard_read_the_same_unfolding():
    """One answer to "what may this be called with", not two that can disagree."""
    source = ast.parse(open(_SERVER_PATH, encoding="utf-8").read())
    readers = {
        fn.name
        for fn in ast.walk(source)
        if isinstance(fn, ast.FunctionDef)
        and any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "declared_arguments"
            for n in ast.walk(fn)
        )
    }
    assert {"_usage_hint", "reject_unknown_arguments"} <= readers, readers


# ---------------------------------------------------------------------------
# AC1 (the "before the handler" half) — asserted on the real dispatcher
# ---------------------------------------------------------------------------


def _call_tool_node() -> ast.AsyncFunctionDef:
    source = ast.parse(open(_SERVER_PATH, encoding="utf-8").read())
    for node in ast.walk(source):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "call_tool":
            return node
    pytest.fail("call_tool not found in server.py — the dispatcher was renamed or removed")


def test_guard_runs_before_the_handler():
    """Order, not presence.

    A guard that runs after handle_tool refuses a write that already happened.
    Presence alone would pass in that arrangement, so the assertion is on which
    call comes first inside the real dispatcher.
    """
    node = _call_tool_node()
    positions = {}
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
            positions.setdefault(sub.func.id, sub.lineno)
        # handle_tool is handed to asyncio.to_thread by reference, not called
        elif isinstance(sub, ast.Name) and sub.id == "handle_tool":
            positions.setdefault("handle_tool", sub.lineno)

    assert "reject_unknown_arguments" in positions, "the dispatcher does not validate at all"
    assert "handle_tool" in positions, "the dispatcher no longer dispatches"
    assert positions["reject_unknown_arguments"] < positions["handle_tool"], positions
