"""The route an agent must take, derived — so the rule can be checked, not read.

the-route-an-agent-must-take-is-enforced-not-described. Measured over this
project's own transcripts (session #233, 4,011 shell commands):

    MCP-first     1,216 of 1,530 CLI invocations HAD an MCP twin and used the
                  shell anyway. MCP's share of all framework calls: 29.1%.
    the wrapper      79 direct `python scripts/*.py` runs — of which 68 went to
                  scripts that have NO wrapper route at all.

The second number is the important one, and it inverts the obvious reading. The
rule "always through `.tausik/tausik`" was UNFOLLOWABLE for those scripts, and an
unfollowable rule is worse than an absent one: it teaches that rules here are
approximate. So the first job is not to demand the route — it is to make sure one
exists, or to say plainly that this module is not an entry point.

THREE STATES, AND THE THIRD IS THE DEFECT:

  ROUTED     — a CLI subcommand reaches it. Running the file directly is a bypass.
  REFUSES    — no route, and the module says so on direct run, naming what to use.
  UNREACHABLE— neither. The rule demands a route that does not exist, and whoever
               follows the rule is stuck. This is what the ratchet forbids.

EVERYTHING HERE IS DERIVED. The CLI↔MCP correspondence is read from the live MCP
dispatch table, not from a list beside it: a hand-kept table of "which command
has a tool" would drift from the tools exactly as every other hand-kept registry
in this project has (decision #335).
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent


#: How a CLI subcommand becomes an MCP tool name: `task done` -> tausik_task_done.
#: Derived shape, not a table — a table would need editing for every new command.
def mcp_twin(command: str) -> str:
    """The MCP tool that would do the same thing, by name. Existence is checked."""
    return "tausik_" + command.strip().replace(" ", "_").replace("-", "_")


@lru_cache(maxsize=1)
def mcp_tools() -> frozenset[str]:
    """Every tool the MCP server dispatches, read from the server itself.

    Empty when the package cannot be imported — and callers treat empty as
    "unknown", never as "no tool exists": reporting an unreachable server as a
    missing twin would accuse the agent of a choice it never had.
    """
    mcp_dir = _REPO / "harness" / "claude" / "mcp" / "project"
    if not mcp_dir.is_dir():
        return frozenset()
    if str(mcp_dir) not in sys.path:
        sys.path.insert(0, str(mcp_dir))
    try:
        import handlers  # noqa: PLC0415 - optional, resolved at call time

        table = getattr(handlers, "_DISPATCH", None)
        return frozenset(table) if isinstance(table, dict) else frozenset()
    except Exception:  # noqa: BLE001 - a broken import must not become an accusation
        return frozenset()


@lru_cache(maxsize=1)
def cli_commands() -> frozenset[str]:
    """Top-level subcommands the CLI parser declares."""
    try:
        out = subprocess.run(
            [sys.executable, str(_HERE / "project.py"), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env={**os.environ, "PYTHONUTF8": "1"},
            # Closed, always. A child that inherits the MCP stdin pipe can read
            # the protocol stream out from under the server.
            stdin=subprocess.DEVNULL,
        ).stdout
    except (subprocess.TimeoutExpired, OSError):
        return frozenset()
    match = re.search(r"\{([a-z0-9,_-]+)\}", out)
    return frozenset(match.group(1).split(",")) if match else frozenset()


def has_main_block(path: Path) -> bool:
    """Does the module do anything when run directly?

    By AST: `if __name__ == "__main__":` in a string or a comment is not an entry
    point, and a text search cannot tell the difference.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return False
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
        ):
            return True
    return False


def refuses_direct_run(path: Path) -> bool:
    """Does the module decline to be run directly, naming what to use instead?"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "refuse_direct_run" in text


def classify(path: Path) -> str:
    """ROUTED | REFUSES | ENTRYPOINT | INERT for one module.

    ENTRYPOINT is a module that legitimately runs on its own — it has a real
    `__main__` and does not refuse. That is not a violation; it is a fact the
    rules must stop contradicting.

    INERT is the defect: run it directly and nothing happens, quietly. Six such
    runs are in the transcripts, and each produced silence the agent then had to
    diagnose.
    """
    if refuses_direct_run(path):
        return "REFUSES"
    if has_main_block(path):
        return "ENTRYPOINT"
    return "INERT"

