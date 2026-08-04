"""codebase-rag: the advertised tool surface and the dispatch must agree.

Pins what `mcp-rag-server-module-split` had to verify by hand. Splitting
server.py moved the seven `Tool(...)` schemas into `rag_tools.py` and the
dispatch into `rag_handlers.py` — two files that can now drift apart in a way
one file could not. A schema with no branch is a tool that answers "Unknown
tool"; a branch with no schema is dead code the host can never reach.

AST rather than import: the schemas are `mcp.types.Tool` instances, and these
assertions must hold on a checkout where the optional `mcp` package is absent.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "harness" / "claude" / "mcp" / "codebase-rag"

# This file scans a whole package rather than importing named modules, so the
# scoped-pytest gate cannot infer from an import which changes should run it.
# Declared explicitly: any edit inside the package must re-check the surface.
CROSSCUTTING_SCOPE = ["harness/claude/mcp/codebase-rag/"]


def _schema_names() -> set[str]:
    """Tool names the server advertises, from `Tool(name=...)` literals."""
    names: set[str] = set()
    for path in sorted(PKG.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Tool":
                for kw in node.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        names.add(str(kw.value.value))
    return names


def _dispatch_names() -> set[str]:
    """Tool names the dispatch branches on, from `name == "..."` comparisons."""
    names: set[str] = set()
    tree = ast.parse((PKG / "rag_handlers.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and getattr(node.left, "id", None) == "name":
            for comp in node.comparators:
                if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                    names.add(comp.value)
    return names


def test_every_advertised_tool_has_a_dispatch_branch() -> None:
    missing = _schema_names() - _dispatch_names()
    assert not missing, f"advertised but unhandled (would answer 'Unknown tool'): {sorted(missing)}"


def test_every_dispatch_branch_is_advertised() -> None:
    orphan = _dispatch_names() - _schema_names()
    assert not orphan, f"handled but never advertised — unreachable: {sorted(orphan)}"


def test_surface_is_not_accidentally_empty() -> None:
    """Guards the checks above against passing on two empty sets.

    Both assertions are set differences, so a parser that silently stopped
    finding anything would make them vacuously true — the failure mode this
    split could actually produce.
    """
    assert len(_schema_names()) >= 7, f"expected the 7 known tools, found {sorted(_schema_names())}"


def test_schemas_and_dispatch_live_in_separate_modules() -> None:
    """The split is the point: server.py holds transport, not tool payload."""
    server_src = (PKG / "server.py").read_text(encoding="utf-8")
    assert "Tool(" not in server_src, "tool schemas belong in rag_tools.py"
    assert "def call_tool_sync" not in server_src, "tool logic belongs in rag_handlers.py"


def test_server_keeps_its_entrypoint() -> None:
    """`.mcp.json` launches this file as a script — it must still run as one.

    The split moved the trailing `if __name__ == "__main__": main()` out with
    the last function and nobody would have noticed until a user's RAG tools
    quietly stopped appearing: the script would start, define everything, and
    exit 0 without serving. Import-level checks cannot see this.
    """
    tree = ast.parse((PKG / "server.py").read_text(encoding="utf-8"))
    guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and getattr(node.test.left, "id", None) == "__name__"
    ]
    assert guards, "server.py lost its `if __name__ == '__main__'` entrypoint"
    called = {
        n.func.id
        for guard in guards
        for n in ast.walk(guard)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "main" in called, f"entrypoint does not call main(); calls {sorted(called)}"
