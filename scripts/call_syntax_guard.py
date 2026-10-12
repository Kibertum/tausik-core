"""Refuse text that carries a swallowed tool call.

tool-call-syntax-leaks-into-entity-text (1.10, github#75). When a host parser
misreads where a parameter ends, the rest of the call — the next parameter, the
closing of the invocation, sometimes a whole second call — lands inside the text
field being written: 64 entities of this project carried it (a task goal ending
in its own closing tag followed by the complexity parameter, whose column was
then left empty — a partial call accepted in silence).

The signature is STRUCTURAL: a closing tag immediately followed by the opening
of another parameter, an invocation, or another tag. Prose that quotes the
syntax («</goal>» followed by words) does not match; on the live database the
card describing this very defect was the only prose mention and it passed.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from tausik_utils import ServiceError

LEAK = re.compile(r"</[A-Za-z_]+>\s*(?:<parameter name=|</invoke>|<invoke name=|<[a-z_]+\"?>)")


def refuse_call_syntax(values: Iterable[Any], names: Iterable[str] | None = None) -> None:
    """Raise ServiceError naming the field whose value carries a tool-call fragment."""
    labels = list(names) if names is not None else None
    for i, value in enumerate(values):
        if isinstance(value, str) and LEAK.search(value):
            field = labels[i] if labels and i < len(labels) else f"value #{i + 1} of this write"
            raise ServiceError(
                f"Refused: {field} contains the tail of a tool call (a closing tag followed by "
                "another parameter or invocation) — the call was parsed partially and the "
                "rest of it landed in the text. Re-send the call with each argument closed."
            )
