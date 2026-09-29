"""The CLI-only registry is true: every entry has a reason and none is an MCP tool
(redact-exists-in-cli-and-is-absent-from-mcp)."""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "harness", "claude", "mcp", "project"))

import mcp_cli_only  # noqa: E402
import tools  # noqa: E402

_NAMES = {
    t["name"] for t in (tools.TOOLS if isinstance(tools.TOOLS, list) else tools.TOOLS.values())
}


@pytest.mark.parametrize("command", sorted(mcp_cli_only.CLI_ONLY))
def test_every_entry_says_why_and_on_whose_decision(command):
    entry = mcp_cli_only.CLI_ONLY[command]
    assert len(entry.get("reason", "").strip()) > 40
    assert entry.get("decided_by", "").startswith("decision #")


@pytest.mark.parametrize("command", sorted(mcp_cli_only.CLI_ONLY))
def test_a_listed_command_is_not_an_mcp_tool(command):
    assert mcp_cli_only.CLI_ONLY[command]["mcp_tool"] not in _NAMES


def test_the_registry_would_catch_a_tool_that_appeared(monkeypatch):
    monkeypatch.setitem(
        mcp_cli_only.CLI_ONLY,
        "status",
        {"reason": "x" * 50, "decided_by": "decision #1", "mcp_tool": "tausik_status"},
    )
    assert mcp_cli_only.CLI_ONLY["status"]["mcp_tool"] in _NAMES


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_the_cli_docs_say_redact_is_cli_only(lang):
    """The reader must be told the absence is DELIBERATE, and where it is enforced.

    Two things changed here and both are the point. The reference is a GROUP of pages now,
    so the claim is read across the group rather than off one file that its section has
    since left. And the assertion no longer demands the decision NUMBER: on a page written
    for the user that number addresses a row in this project's database and nobody else's,
    while `scripts/mcp_cli_only.py` is an address every reader can open. Pinning the number
    here is part of what kept it on the page.
    """
    import gate_doc_coverage

    text = gate_doc_coverage.cli_reference_text(_ROOT, lang)
    assert "scripts/mcp_cli_only.py" in text, "the page names where the absence is enforced"
    assert "redact" in text
