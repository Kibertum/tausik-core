"""Name the tool TAUSIK ships, at the moment an alternative was chosen.

a-tool-is-chosen-at-the-moment-the-alternative-appears (and, before it,
the-route-an-agent-must-take-is-enforced-not-described). "MCP-first" is a hard
constraint in the rules every agent reads. Measured over this project's own
transcripts (session #233, 4,011 shell commands): of 1,530 CLI invocations,
1,216 — 79.5% — had an MCP twin and went through the shell anyway. MCP's share of
all framework calls was 29.1%.

Nothing noticed. That is the whole finding: a rule stated in prose and checked by
nobody is followed when the agent happens to remember, and "sometimes" is what
that measures to.

WHY THIS NUDGES AND DOES NOT BLOCK. 20.5% of CLI invocations have no MCP twin at
all, and two shell habits are legitimate and load-bearing here: chaining
(`verify && task done` in one call, which the MCP surface cannot express) and
feeding a long multi-line argument through `"$(cat file)"`. A block would refuse
those, and a false block on a routine operation trains circumvention — costing
more than the miss it prevents (convention #291). So this makes the choice
VISIBLE at the moment it is made, and `doctor` carries the running share so the
number cannot be quietly ignored.

TWO CHOICES, ONE SHAPE. The second is `grep` for a DEFINITION versus
`tausik symbol`, measured in the same window at 2 uses against 226 greps —
a tool built an hour earlier and not being chosen. Both cases are the same
defect: a rule joined to the moment of choice by nothing but memory.

ONCE PER SUBJECT PER SESSION. A note repeated on every call is a note the reader
learns to skip, and a skipped note is worse than none: it consumes the attention
that the next real warning needs.
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.dirname(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#: `.tausik/tausik task done <slug>` -> ("task done"). Two words at most: no
#: TAUSIK command nests deeper, and a greedy match would turn a slug into part of
#: the command name and then find no twin for it.
_CLI = re.compile(r"\.tausik[/\\]tausik(?:\.cmd)?\s+([a-z][a-z-]*)(?:\s+([a-z][a-z-]*))?")

#: `grep -n "def foo"` / `grep -rn "class Bar"` — a search for a DEFINITION,
#: which is what `tausik symbol` answers in one call with the body and the
#: callers. NOT a plain text search: `grep "definition"` in prose, a path
#: containing "def", or a word search must stay silent, because a nudge that
#: fires on ordinary work is one the reader learns to skip.
_GREP_DEF = re.compile(
    # `rg` as well as `grep`: ripgrep is the same intent under another name, and
    # a detector knowing only one would go quiet for half the ecosystem. Found by
    # a test that asserted the case rather than by reasoning about it.
    r"\b(?:grep|rg)\b[^|;&]*?[\"']\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)",
)

#: Where the "already said this" marks live, one file per session.
_SEEN_BASENAME = ".mcp_first_seen.json"


def _seen_path(project_dir: str, session_id: str) -> str:
    return os.path.join(project_dir, ".tausik", f"{_SEEN_BASENAME}.{session_id}")


def commands_in(text: str) -> list[str]:
    """Every `tausik <cmd> [<sub>]` invocation in a shell command line."""
    found: list[str] = []
    for first, second in _CLI.findall(text or ""):
        if second and not second.startswith("-"):
            found.append(f"{first} {second}")
        found.append(first)
    return found


def twins_for(commands: list[str]) -> dict[str, str]:
    """{command: mcp tool} for those that HAVE one, longest match winning.

    Longest first so `task done` is reported rather than `task`: the two-word
    form is the one with a twin, and reporting the shorter would name a tool that
    does something else.
    """
    try:
        from route_map import mcp_tools, mcp_twin
    except Exception:  # noqa: BLE001 - the nudge must never break a command
        return {}
    tools = mcp_tools()
    if not tools:
        # Unknown, not empty. Reporting "no twin exists" because the server could
        # not be read would accuse the agent of a choice it never had.
        return {}
    out: dict[str, str] = {}
    for command in sorted(set(commands), key=len, reverse=True):
        if any(command != other and other.startswith(command + " ") for other in out):
            continue
        twin = mcp_twin(command)
        if twin in tools:
            out[command] = twin
    return out


def symbols_in(text: str) -> list[str]:
    """Names searched for as DEFINITIONS in a shell command line."""
    return sorted({m.group(1) for m in _GREP_DEF.finditer(text or "")})


def main() -> None:
    # This hook's message carries non-ASCII. Written through an interpreter that
    # was not started in UTF-8 mode it leaves in the machine's locale encoding,
    # which on Windows turns the note into mojibake — a warning nobody reads.
    try:
        from _common import force_utf8_io

        force_utf8_io()
    except Exception:  # noqa: BLE001 - the guard is a courtesy, not a dependency
        pass

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        sys.exit(0)

    tool = str(payload.get("tool_name") or "")
    if tool not in ("Bash", "PowerShell"):
        sys.exit(0)
    command_line = str((payload.get("tool_input") or {}).get("command") or "")
    if not command_line:
        sys.exit(0)

    twins = twins_for(commands_in(command_line))
    symbols = symbols_in(command_line)
    if not twins and not symbols:
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    session_id = str(payload.get("session_id") or "current")
    path = _seen_path(project_dir, session_id)
    try:
        with open(path, encoding="utf-8") as fh:
            seen = set(json.load(fh))
    except (OSError, ValueError):
        seen = set()

    fresh = {cmd: twin for cmd, twin in twins.items() if cmd not in seen}
    # One mark per SUBJECT: the command for an MCP twin, `symbol` for the
    # definition search — so the two notes do not silence each other.
    fresh_symbols = [name for name in symbols if "symbol" not in seen]

    if not fresh and not fresh_symbols:
        sys.exit(0)

    parts: list[str] = []
    if fresh:
        parts.append(
            "[TAUSIK MCP-first] this went through the shell, and an MCP tool does "
            "the same thing:\n"
            + "\n".join(f"  `{cmd}` -> `{twin}`" for cmd, twin in sorted(fresh.items()))
            + "\nMCP-first is a hard constraint in the rules. Chaining and long "
            "file-fed arguments are legitimate reasons to stay in the shell — this "
            "names the alternative, it does not refuse."
        )
    if fresh_symbols:
        example = fresh_symbols[0]
        parts.append(
            "[TAUSIK symbol] this greps for a DEFINITION. One call answers it with "
            "the body and the callers, so no file read follows:\n"
            f"  .tausik/tausik symbol {example}\n"
            "Measured on this project: grep+read is 2 calls, `symbol` is 1 — the "
            "saving is in calls, and a call re-sends the whole conversation."
        )
    print("\n\n".join(parts) + "\nSaid once per subject per session.", file=sys.stderr)

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            marks = seen | set(fresh) | ({"symbol"} if fresh_symbols else set())
            json.dump(sorted(marks), fh)
    except OSError:
        pass  # the mark is a convenience; failing to write it repeats a note
    sys.exit(0)


if __name__ == "__main__":
    main()
