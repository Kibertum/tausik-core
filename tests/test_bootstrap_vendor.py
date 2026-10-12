"""Vendor agents cross the Kilo schema boundary at the deploy step.

Task vendor-agents-tools-as-object-at-the-deploy. The 1.11.2 fix edited the
DEPLOYED copies and was wiped by every redeploy (twice) — the vendor source is
third-party upstream and keeps Claude Code's comma-string ``tools:`` spelling,
while Kilo's agent schema wants an object and refuses the whole definition at
load. The normalization belongs at the boundary (copy_vendor_assets), where
both sides are visible.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from bootstrap_vendor import copy_vendor_assets, normalize_agent_tools

#: This file reads the local vendor corpus (a source tree) in its live lane.
CROSSCUTTING_SCOPE = [".tausik/vendor"]


def _agent(frontmatter_tools: str) -> str:
    return (
        "---\n"
        "name: probe-agent\n"
        "description: probe\n"
        f"{frontmatter_tools}"
        "---\n\n"
        "Body line. A later line saying\n"
        "tools: Read, Bash, Write\n"
        "is prose, not schema.\n"
    )


# --- the transform -------------------------------------------------------------


def test_scalar_tools_becomes_an_object():
    out = normalize_agent_tools(_agent("tools: Read, Bash, Write\n"))
    assert "tools:\n  Read: true\n  Bash: true\n  Write: true\n" in out
    fm = out.split("---")[1]  # the BODY keeps its prose tools: line on purpose
    assert "tools: Read" not in fm


def test_object_and_absent_tools_pass_through_untouched():
    already_object = _agent("tools:\n  Read: true\n")
    assert normalize_agent_tools(already_object) == already_object
    no_tools = _agent("")
    assert normalize_agent_tools(no_tools) == no_tools


def test_body_tools_line_is_prose_not_schema():
    """The negative lane for the naive scan: `tools:` AFTER the closing --- is
    body text and must survive byte-identical."""
    no_fm_tools = _agent("")
    assert "tools: Read, Bash, Write\n" in normalize_agent_tools(no_fm_tools)


def test_copy_vendor_assets_normalizes_on_the_way_into_the_profile(tmp_path):
    vendor = tmp_path / "vendor" / "seo" / "agents"
    vendor.mkdir(parents=True)
    (vendor / "seo-visual.md").write_text(_agent("tools: Read, Bash, Write\n"), encoding="utf-8")
    target = tmp_path / ".kilo"
    copy_vendor_assets(str(tmp_path / "vendor"), str(target))
    deployed = (target / "agents" / "vendor_seo" / "seo-visual.md").read_text(encoding="utf-8")
    assert "tools:\n  Read: true\n  Bash: true\n  Write: true" in deployed


def test_live_seo_agents_are_object_after_the_boundary(tmp_path):
    """On this checkout the real vendor corpus (7 seo agents) deploys valid."""
    vendor_root = os.path.join(".tausik", "vendor")
    seo = os.path.join(vendor_root, "seo", "agents")
    if not os.path.isdir(seo):
        import pytest

        pytest.skip("no local vendor corpus in this checkout")
    target = tmp_path / ".kilo"
    copy_vendor_assets(vendor_root, str(target))
    deployed_dir = target / "agents" / "vendor_seo"
    files = sorted(deployed_dir.glob("*.md"))
    assert len(files) >= 7
    for f in files:
        text = f.read_text(encoding="utf-8")
        fm = text.split("---")[1]
        assert "tools: " not in fm, f"{f.name}: scalar tools survived the boundary"
