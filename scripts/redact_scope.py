"""The ONE declaration of what a redaction may reach, and how it marks it.

Decision #258: striking a line out of project memory is an OVERWRITE THAT LEAVES
A TRACE, not a deletion. This module holds the half of that contract that says
*where* an overwrite is allowed to land; ``redact_engine`` holds the half that
performs it and records the trace.

Why the map lives here and nowhere else: a second statement of "which columns
carry prose" is free to drift from the first, and the drift shows up as a CLEAN
RUN rather than as an error — the redaction quietly stops reaching a column and
reports success (#249). Every consumer asks this module; a column added here
widens the command in the same commit.

The map is deliberately NARROW — narrative columns only. Structural columns
(``slug``, ``status``, timestamps, foreign keys) are excluded on purpose: they
are addresses, not prose, and rewriting an address breaks the rows that point at
it while removing nothing a human wrote.
"""

from __future__ import annotations

# table -> the columns holding text a human (or an agent) composed.
#
# Checked against the live schema by
# tests/test_redact.py::test_every_declared_column_exists_in_the_schema, so a
# column renamed in backend_schema.py cannot silently narrow what a redaction
# reaches.
REDACTABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    # `notes` and the journal are the two places an agent writes freely, and
    # between them they held 27 of the 69 leaking lines measured in session #180.
    "tasks": (
        "title",
        "goal",
        "plan",
        "notes",
        "acceptance_criteria",
        "scope",
        "scope_exclude",
        "rollback_plan",
    ),
    "task_logs": ("message",),
    "memory": ("title", "content"),
    "decisions": ("decision", "rationale"),
    "stories": ("title", "description"),
    "epics": ("title", "description"),
}


def marker(label: str) -> str:
    """The visible stand-in left where the text was.

    Carries the CLASS of the thing removed and never its value — the whole point
    of a redaction is that the value is gone, and a marker quoting it would put
    the leak straight back into the column it was removed from.

    Visible by design. A redaction that shortened the sentence without saying so
    would be indistinguishable from a sentence that was always that short, and
    the reader would have no way to know something once stood here.
    """
    return f"[вычеркнуто: {label}]"
