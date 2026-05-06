"""MCP tool counts from repository sources (project + brain TOOLS, RAG server).

Shared by doc generators and tests — single source for numeric drift checks.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def count_rag_tool_defs(repo_root: Path) -> int:
    """Count ``Tool(`` definitions in codebase-rag ``server.py``."""
    rag_server = repo_root / "harness" / "claude" / "mcp" / "codebase-rag" / "server.py"
    text = rag_server.read_text(encoding="utf-8")
    return len(re.findall(r"^\s+Tool\(", text, re.MULTILINE))


def count_mcp_tool_totals(repo_root: Path) -> tuple[int, int, int]:
    """Return ``(n_project, n_brain, n_rag)`` using ``len(TOOLS)`` where applicable."""
    proj = str(repo_root / "harness" / "claude" / "mcp" / "project")
    brain = str(repo_root / "harness" / "claude" / "mcp" / "brain")

    sys.path.insert(0, proj)
    import tools as project_tools  # type: ignore[import-not-found]  # noqa: E402

    n_p = len(project_tools.TOOLS)
    sys.path.remove(proj)
    del sys.modules["tools"]

    sys.path.insert(0, brain)
    import tools as brain_tools  # type: ignore[import-not-found, no-redef]  # noqa: E402

    n_b = len(brain_tools.TOOLS)
    sys.path.remove(brain)
    del sys.modules["tools"]

    n_r = count_rag_tool_defs(repo_root)
    return n_p, n_b, n_r


def mcp_counts_flat(repo_root: Path) -> dict[str, int]:
    """Structured counts for JSON export."""
    n_p, n_b, n_r = count_mcp_tool_totals(repo_root)
    main = n_p + n_b
    return {
        "mcp_brain_tools": n_b,
        "mcp_main_tools": main,
        "mcp_project_tools": n_p,
        "mcp_rag_tools": n_r,
        "mcp_tools_with_optional_rag": main + n_r,
    }
