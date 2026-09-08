"""What the FRAMEWORK wrote during a close, subtracted from the agent's scope.

MEASURED (session #235, live database). Of 2,278 verify runs, 846 recorded an
under-declared scope; the recent window is what matters, and there it is 135 of
the last 300 (45%) and 39 of the last 100 (39%). What sits at the top of the
undeclared list is not the agent's work:

    54  AGENTS.md
    54  CLAUDE.md
    12  ROADMAP.md

`update-claudemd` rewrites the first two and `doc roadmap` rewrites the third,
and the framework runs both ITSELF while closing. The agent cannot declare them
in advance, because at declaration time they have not changed yet. Of those 135
under-declarations, 26 (19%) consist of nothing else, and another 39 (29%) are
mixed.

THE PRINCIPLE IS NOT NEW HERE. Convention #409 and decision #283 already say it
for the neighbouring checks: a check whose subject is "what did the AGENT
change" must subtract what the framework itself wrote. `verify_own_export`
subtracts the task's own export for exactly this reason. This module applies
the same rule to the framework's generated documents.

THE LINE THIS MUST NOT CROSS, and why the decision is taken per-DIFF rather
than per-NAME. `CLAUDE.md` and `AGENTS.md` are only PARTLY generated: between
the `DYNAMIC` markers the framework writes, and everywhere else a human or an
agent does — session #233 edited exactly that static part on purpose.
Subtracting a whole file by its name would hide real work, which is the same
defect with the sign flipped, and "the name matched, so it must be the thing"
is what convention #638 exists against. So a partly-generated file is
subtracted only when the change is provably confined to the generated region.

WHAT IS DELIBERATELY NOT SUBTRACTED. `CHANGELOG.md` and its mirror are written
by the agent. They appear in the undeclared list often, and that is a REAL
under-declaration — the thing this module must keep visible rather than tidy
away.
"""

from __future__ import annotations

import os
import subprocess

#: Written by the framework and by nothing else. `doc roadmap` and
#: `gen_doc_constants` own these completely, so their presence in a changed-file
#: list says nothing about the agent.
WHOLLY_GENERATED: tuple[str, ...] = (
    "ROADMAP.md",
    "docs/_generated/",
)

#: Partly generated: the framework owns the region between the markers below and
#: nothing else in the file. Subtracted ONLY when the diff stays inside it.
PARTLY_GENERATED: tuple[str, ...] = (
    "CLAUDE.md",
    "AGENTS.md",
)

_DYNAMIC_START = "<!-- DYNAMIC:START -->"
_DYNAMIC_END = "<!-- DYNAMIC:END -->"


def _normalise(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _is_wholly_generated(rel: str) -> bool:
    return any(rel == entry or rel.startswith(entry) for entry in WHOLLY_GENERATED)


def _changed_line_numbers(rel: str, root: str) -> list[int] | None:
    """1-based new-side line numbers touched by the working diff, or None.

    None means "could not read the diff", and every caller treats that as "do
    not subtract": being unable to check is not permission (decision #334).
    """
    try:
        result = subprocess.run(
            ["git", "diff", "-U0", "--", rel],
            cwd=root,
            capture_output=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.decode("utf-8", errors="replace")
    if not text.strip():
        # No unstaged diff. The change may be staged or already committed, and
        # this module cannot tell WHICH region it touched. Unknown, not empty.
        return None

    lines: list[int] = []
    for hunk in text.splitlines():
        if not hunk.startswith("@@"):
            continue
        # `@@ -a,b +c,d @@` — the new-side start and length.
        try:
            new_side = hunk.split("+", 1)[1].split("@@", 1)[0].strip()
            start_text, _, length_text = new_side.partition(",")
            start = int(start_text)
            length = int(length_text) if length_text else 1
        except (IndexError, ValueError):
            return None
        lines.extend(range(start, start + max(length, 1)))
    return lines


def _dynamic_region(rel: str, root: str) -> tuple[int, int] | None:
    """(first, last) 1-based line numbers of the generated block, or None."""
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            content = fh.read().splitlines()
    except OSError:
        return None
    start = end = None
    for number, line in enumerate(content, start=1):
        if _DYNAMIC_START in line:
            start = number
        elif _DYNAMIC_END in line:
            end = number
    if start is None or end is None or end < start:
        return None
    return start, end


def change_is_only_generated(rel: str, root: str) -> bool:
    """Does the change to `rel` lie entirely inside its generated region?

    False whenever that cannot be established — a missing marker, an unreadable
    diff, a hunk this parser does not understand. The conservative answer keeps
    the file in the agent's scope, which is the direction that cannot hide work.
    """
    region = _dynamic_region(rel, root)
    if region is None:
        return False
    changed = _changed_line_numbers(rel, root)
    if not changed:
        return False
    first, last = region
    return all(first <= number <= last for number in changed)


def subtract_framework_output(
    file_paths: list[str] | None, *, root: str | None = None
) -> tuple[list[str], list[str]]:
    """`file_paths` minus what the framework wrote itself. Order preserved.

    Returns `(kept, removed)`, with `removed` spelled as the caller spelled it —
    the caller is reporting on its own list, and renaming a file mid-message
    makes the reader look for a second one.
    """
    files = [f for f in (file_paths or []) if f and isinstance(f, str)]
    base = root or os.getcwd()
    kept: list[str] = []
    removed: list[str] = []
    for raw in files:
        normalised = _normalise(raw)
        if _is_wholly_generated(normalised):
            removed.append(raw)
        elif normalised in PARTLY_GENERATED and change_is_only_generated(normalised, base):
            removed.append(raw)
        else:
            kept.append(raw)
    return kept, removed
