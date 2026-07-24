r"""Which tool speaks which shell — the one place that knows.

`powershell-tool-bypasses-bash-firewall`. Before this module the answer was
spelled `event.get("tool_name") != "Bash"`, separately, in every hook that
gates a shell command. That is an enumeration, and convention #289 is about
exactly this shape: a checker must ask the PRODUCER for the set of objects it
covers instead of listing them itself, because the list and the world drift
apart silently. They did. A second shell tool appeared on the primary platform
and every one of those literals kept returning "not my channel" — no error, no
warning, no failing test, just supervision that had quietly stopped applying.

So the mapping lives here once. A hook asks `is_shell_tool` and
`write_targets`; adding a third shell means adding one row to `_DIALECTS` and
one parser, not auditing every gate for a string comparison someone forgot.
"""

from __future__ import annotations

import os
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

import bash_cmd_scan  # noqa: E402
import bash_write_parse  # noqa: E402
import pwsh_cmd_norm  # noqa: E402
import pwsh_write_parse  # noqa: E402

#: Tool name -> the module that can read that tool's command syntax. Keyed by
#: the name the harness puts in `tool_name`, because that is the only identifier
#: a hook actually receives.
_DIALECTS = {
    "Bash": bash_write_parse,
    "PowerShell": pwsh_write_parse,
}

#: Tool name -> the scanner that separates that dialect's COMMANDS from the
#: prose it merely quotes. A separate table from `_DIALECTS` only because the
#: two answers live in different modules; they are keyed identically and
#: `test_every_dialect_has_both_a_parser_and_a_scanner` pins that they stay so.
_SCANNERS = {
    "Bash": bash_cmd_scan.scan_target,
    "PowerShell": pwsh_cmd_norm.scan_target,
}

#: Every tool whose input is a shell command line. Hooks registered on these
#: must also be REGISTERED for them in `bootstrap_hooks` — this tuple is the
#: source that `test_hooks` asserts the registration against, so a tool added
#: here without a matcher fails a test instead of silently going ungated.
SHELL_TOOLS = tuple(_DIALECTS)


def is_shell_tool(tool_name: object) -> bool:
    """True when this event carries a shell command rather than a file path."""
    return isinstance(tool_name, str) and tool_name in _DIALECTS


def command_of(event: dict) -> str | None:
    """The command string in a shell-tool event, or None if there is none."""
    if not is_shell_tool(event.get("tool_name")):
        return None
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    return command


def scan_target(tool_name: str, command: str) -> str:
    """The executable part of `command`, read in the dialect `tool_name` speaks.

    An unknown tool name falls back to the POSIX scanner: that is how every
    non-Windows host and every future shell arrives, and over-scanning is the
    safe direction — a false positive costs a question, a miss costs the tree.
    """
    scanner = _SCANNERS.get(tool_name, bash_cmd_scan.scan_target)
    return scanner(command)


def tokenize(tool_name: str, command: str) -> list[str] | None:
    """`command` split into words the way `tool_name`'s shell would, or None.

    None means the line does not parse in that dialect; a caller decides what
    to do about it, and the honest options are "fail closed" or "fall back to a
    regex", never "ask the OTHER dialect".

    That last option is not hypothetical. The push gate briefly tried both
    tokenizers and blocked if EITHER saw a `git push` — sound against evasion,
    and wrong in practice: the POSIX lexer does not know a PowerShell
    here-string, breaks out of it at the first apostrophe, and then reads the
    `git push` in a commit message's PROSE as a command. Of two judges, the one
    that cannot read the language wins every disagreement. Dialect follows the
    tool, and nothing else.
    """
    module = _DIALECTS.get(tool_name, bash_write_parse)
    return module.tokenize(command)


def write_targets(tool_name: str, command: str) -> list[str]:
    """Paths `command` appears to write, read in the dialect `tool_name` speaks.

    Falls back to the POSIX parser for an unknown tool name. That direction is
    deliberate: an unrecognised shell still gets SOME write detection, and an
    over-detected target costs a task the write would have needed anyway, while
    returning nothing would reproduce the hole this module exists to close.
    """
    module = _DIALECTS.get(tool_name, bash_write_parse)
    return module.write_targets(command)


def write_targets_with_confidence(tool_name: str, command: str) -> tuple[list[str], str]:
    """`(targets, confidence)` in the dialect `tool_name` speaks.

    See `write_confidence`. Both dialects report in the same vocabulary, so a
    consumer that fails closed on uncertainty behaves identically on either
    channel — which is the property that stops the weaker one from becoming the
    route around the guard.
    """
    module = _DIALECTS.get(tool_name, bash_write_parse)
    return module.write_targets_with_confidence(command)
