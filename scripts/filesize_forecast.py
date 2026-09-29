"""The line cap, answered in the turn that writes the file instead of at verify.

MEASURED. Across 285 red verify runs, `filesize` is 16.1% and it is not history: 20 of them
fell in September alone, second only to `bootstrap_drift`. A red run is expensive — tasks
with no red run cost a median 51k tokens, one red 78k, two 123k — and this particular red is
avoidable by arithmetic: the cap is a number, the file is on disk, and the write that
crosses it is in the caller's hand at that moment.

IT WARNS AND NEVER BLOCKS. A write refused mid-task leaves the author with a half-applied
change and no way to finish the thought; splitting a file is a decision about structure, not
something to be forced at the moment of typing. So this returns words, and the write goes
through either way.

IT ASKS THE GATE'S OWN QUESTION. The cap and the exemptions come from `gate_filesize`
through `is_exempt`, extracted for exactly this. A second copy of those rules would drift,
and the two would then disagree precisely when it matters — warning about a file the gate
exempts, or staying silent about one it refuses.
"""

from __future__ import annotations

import os
from typing import Any

from gate_filesize import DEFAULT_MAX_LINES, count_lines, is_exempt

#: How close to the cap is close enough to say something. A file that lands ON the cap is
#: one edit away from the refusal, and hearing about it then is still in time to act.
NEAR = 25


def _lines(text: str) -> int:
    """Lines as the gate counts them: a trailing newline does not open a new line."""
    if not text:
        return 0
    return len(text.splitlines())


def resulting_lines(tool: str, tool_input: dict[str, Any], path: str) -> int | None:
    """How many lines the file will have after this call, or None when that is unknowable.

    None is the honest answer for a tool whose result cannot be computed from the payload —
    a guess there would warn about a size nobody is about to write.
    """
    if tool == "Write":
        content = tool_input.get("content")
        return _lines(content) if isinstance(content, str) else None
    if tool in ("Edit", "NotebookEdit"):
        old, new = tool_input.get("old_string"), tool_input.get("new_string")
        if not isinstance(old, str) or not isinstance(new, str):
            return None
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                current = _lines(fh.read())
        except OSError:
            return None
        delta = _lines(new) - _lines(old)
        if tool_input.get("replace_all"):
            # The number of occurrences is not in the payload, so the delta is a lower
            # bound at best. Saying nothing beats naming a figure that is wrong whenever
            # the string appears more than once.
            return None
        return current + delta
    return None


def forecast(tool: str, tool_input: dict[str, Any], root: str, gate: dict | None = None) -> str:
    """One line of warning, or "" when there is nothing to say.

    Everything unknown resolves to "": an unreadable file, a payload this cannot read, a
    tool whose result is not computable. The cost of silence here is one red verify, which
    is what happened before; the cost of a wrong warning is an author who stops reading
    them.
    """
    path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(path, str) or not path:
        return ""
    gate = gate or {}
    cap = int(gate.get("max_lines") or DEFAULT_MAX_LINES)
    abs_path = path if os.path.isabs(path) else os.path.join(root, path)
    if is_exempt(abs_path, gate):
        return ""
    lines = resulting_lines(tool, tool_input, abs_path)
    if lines is None or lines < cap - NEAR:
        return ""
    rel = os.path.relpath(abs_path, root).replace("\\", "/")
    if lines > cap:
        return (
            f"LINE CAP: {rel} will be {lines} lines, over the cap of {cap}. "
            "`filesize` refuses the close on it — splitting it now costs less than a red "
            "verify later, and the split is yours to design."
        )
    return (
        f"LINE CAP: {rel} will be {lines} lines, {cap - lines} short of the cap of {cap}. "
        "The next addition is likely to cross it."
    )


def current_size_note(path: str, root: str, gate: dict | None = None) -> str:
    """The same warning for a file already on disk, for callers with no payload."""
    gate = gate or {}
    abs_path = path if os.path.isabs(path) else os.path.join(root, path)
    if not os.path.isfile(abs_path) or is_exempt(abs_path, gate):
        return ""
    cap = int(gate.get("max_lines") or DEFAULT_MAX_LINES)
    lines = count_lines(abs_path)
    if lines <= cap:
        return ""
    rel = os.path.relpath(abs_path, root).replace("\\", "/")
    return f"LINE CAP: {rel} is {lines} lines, over the cap of {cap}."


if __name__ == "__main__":  # pragma: no cover - exercised via the hook
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
