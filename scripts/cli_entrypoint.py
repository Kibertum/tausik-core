"""Refusal for CLI modules that are libraries, not entry points.

`scripts/project_cli*.py` hold `cmd_*` handlers; the only entry point is
`scripts/project.py`, wrapped by `.tausik/tausik`. Running a handler module
directly used to define its functions, call none of them, print nothing and
exit 0 — indistinguishable from success. Someone signing a skill that way
believed the signature had been written.
"""

from __future__ import annotations

import os
import sys

_MESSAGE = (
    "{name} is a library module, not an entry point: running it defines the\n"
    "command handlers and calls none of them.\n"
    "\n"
    "{route}\n"
    "\n"
    "See `.tausik/tausik --help` or docs/ru/cli.md."
)

_GENERIC_ROUTE = (
    "Use the CLI wrapper instead, which resolves the project venv:\n"
    "  .tausik/tausik <command> [args]        (.tausik\\tausik.cmd on Windows)"
)


def refuse_direct_run(module_file: str, route: str | None = None) -> None:
    """Print why this module is not runnable, NAME the route, and exit non-zero.

    `route` is the command that does what the caller wanted. Without it the
    refusal says "use the wrapper" and leaves the reader to find WHICH command —
    which is the search the refusal exists to save. Measured in session #233: two
    modules with no `__main__` were run directly six times, each run producing
    silence, because Python imported them and exited 0.

    Exits 2 (argparse's usage-error code) so scripts and CI treat it as the
    misuse it is. Silence with exit 0 is the bug being fixed here.
    """
    text = _MESSAGE.format(
        name=os.path.basename(module_file),
        route=f"Use this instead:\n  {route}" if route else _GENERIC_ROUTE,
    )
    print(text, file=sys.stderr)
    raise SystemExit(2)
