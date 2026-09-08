"""CLI handler for `tausik symbol` — the definition, not its address.

Measured before this existed (session #233, eight transcripts): code exploration
was about 47% of everything tools returned — 9.6% through Read/Grep/Glob and
37.1% through `grep/sed/find/ls` inside Bash, 1,192 calls at 1,501 characters
apiece. The pattern being replaced is grep for the definition, then read the
file around it, then sometimes read again for the callers.

Derived from Graft (github.com/trailhq/Graft), whose deterministic half answers
with the source inlined so no follow-up read is needed. The model-written
explanation layer is deliberately not copied: it needs a key, a network and
money, and the measurable saving is in the deterministic half.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def cmd_symbol(_svc_unused: Any, args: Any) -> None:
    """Print one answer about a symbol: definition, location, callers."""
    _here = os.path.dirname(os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)
    from symbol_answer import answer
    from symbol_index import DEFAULT_BODY_LINES

    query = getattr(args, "name", None)
    if not query:
        print("error: give a symbol name, e.g. `tausik symbol tags_unmoved`", file=sys.stderr)
        sys.exit(1)

    print(
        answer(
            os.getcwd(),
            query,
            max_lines=int(getattr(args, "lines", None) or DEFAULT_BODY_LINES),
            with_callers=not getattr(args, "no_callers", False),
        ),
        end="",
    )


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
