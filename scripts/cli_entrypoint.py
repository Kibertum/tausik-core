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
    "Use the CLI wrapper instead, which resolves the project venv:\n"
    "  .tausik/tausik <command> [args]        (.tausik\\tausik.cmd on Windows)\n"
    "\n"
    "See `.tausik/tausik --help` or docs/ru/cli.md."
)


def refuse_direct_run(module_file: str) -> None:
    """Print why this module is not runnable and exit non-zero.

    Exits 2 (argparse's usage-error code) so scripts and CI treat it as the
    misuse it is. Silence with exit 0 is the bug being fixed here.
    """
    print(_MESSAGE.format(name=os.path.basename(module_file)), file=sys.stderr)
    raise SystemExit(2)
