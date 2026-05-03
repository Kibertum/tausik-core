"""r14-codebase-rag-doc: docs/en|ru/mcp.md main tool counts match code."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from mcp_tool_counts import count_mcp_tool_totals  # noqa: E402


def _code_counts() -> tuple[int, int, int]:
    return count_mcp_tool_totals(REPO)


def _parse_doc_main_total(path: Path) -> tuple[int, int | None]:
    """Return (main_bold_count, optional_total_with_rag from blockquote)."""
    text = path.read_text(encoding="utf-8")
    main = re.search(
        r"\*\*(\d+)\s*(?:tools?|инструментов)\*\*",
        text,
        re.IGNORECASE,
    )
    assert main, f"{path}: missing **N tools** / **N инструментов** in header"
    total_m = re.search(
        r"(?:total with it is|итого с ним)\s+(\d+)\s*(?:tools?|инструмент\w*)",
        text,
        re.IGNORECASE,
    )
    total = int(total_m.group(1)) if total_m else None
    return int(main.group(1)), total


@pytest.mark.parametrize(
    "rel",
    ["docs/en/mcp.md", "docs/ru/mcp.md"],
)
def test_mcp_markdown_main_count_matches_code(rel):
    n_project, n_brain, n_rag = _code_counts()
    main_expected = n_project + n_brain
    path = REPO / rel
    main_doc, total_doc = _parse_doc_main_total(path)
    assert main_doc == main_expected, (
        f"{rel}: doc claims {main_doc} main tools, code has "
        f"{n_project}+{n_brain}={main_expected}"
    )
    if total_doc is not None:
        assert total_doc == main_expected + n_rag, (
            f"{rel}: optional total {total_doc} != {main_expected}+{n_rag}"
        )


def test_rag_tool_count_matches_server_py():
    _, _, n_rag = _code_counts()
    assert n_rag == 7


def test_readme_mcp_hero_bullets_match_code():
    """README EN/RU hero line stays aligned with len(TOOLS) (same contract as mcp.md)."""
    n_project, n_brain, _ = _code_counts()
    main_expected = n_project + n_brain
    patterns = [
        (
            "README.md",
            re.compile(
                r"\*\*(\d+)\s+MCP tools?\*\*\s*\((\d+)\s+project\s*\+\s*(\d+)\s+brain\)",
                re.IGNORECASE,
            ),
        ),
        (
            "README.ru.md",
            re.compile(
                r"\*\*(\d+)\s+MCP[- ]инструмент\w*\*\*\s*\((\d+)\s+project\s*\+\s*(\d+)\s+brain\)",
                re.IGNORECASE,
            ),
        ),
    ]
    for rel, rx in patterns:
        text = (REPO / rel).read_text(encoding="utf-8")
        m = rx.search(text)
        assert m, f"{rel}: missing **N MCP…** (X project + Y brain) hero bullet"
        assert int(m.group(1)) == main_expected, f"{rel}: total mismatch"
        assert int(m.group(2)) == n_project, f"{rel}: project count mismatch"
        assert int(m.group(3)) == n_brain, f"{rel}: brain count mismatch"


def test_docs_readme_index_mcp_count_matches_code():
    n_project, n_brain, _ = _code_counts()
    main_expected = n_project + n_brain
    path = REPO / "docs" / "README.md"
    text = path.read_text(encoding="utf-8")
    row = re.search(
        r"MCP Tools.*?(\d+)\s+tools for the AI agent",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    assert row, "docs/README.md: MCP Tools row missing N tools"
    assert int(row.group(1)) == main_expected


def test_agents_md_mcp_counts_match_code():
    """AGENTS.md — Documentation Map, model/host table, repo tree stay aligned with TOOLS."""
    n_project, n_brain, n_rag = _code_counts()
    main_expected = n_project + n_brain
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert (
        f"{n_project} project + {n_brain} brain = {main_expected}" in text
    ), "AGENTS.md: missing canonical N project + N brain = main"
    assert str(main_expected + n_rag) in text, (
        "AGENTS.md: missing total-with-RAG count (main + codebase-rag)"
    )
    tree = re.search(
        rf"tausik-project\s*\({n_project}\)\s*\+\s*tausik-brain\s*\({n_brain}\)\s*=\s*{main_expected}\s+main",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    assert tree, "AGENTS.md: repository tree line must echo tausik-project (N) + brain (N) = main"
