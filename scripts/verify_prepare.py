"""The two calls every task pays before a check can be green.

MEASURED. Two gates go red for reasons known in advance and fixed by a fixed command:
`ruff_format` unless `ruff format` has run, and `bootstrap_drift` after any edit under
`scripts/` unless the profile has been redeployed. Both are deterministic, neither is a
judgement, and each costs its own call — at the project's measured 482 000 tokens of prefix
re-sent per call, about a million tokens per task, against roughly 400 closures a month.

WHY THIS IS NOT THE GATE HEALING ITSELF. `bootstrap_drift` refuses to rebuild the copies it
evaluates, and rightly: a gate that mutates the state it judges certifies its own repair.
What runs here is not the gate — it is the AGENT, asking for the preparation by name before
the gates look at anything. The asking is explicit, the step list is data rather than
something assembled on the way, and the outcome is reported so a green never quietly means
"green after something changed the tree".

WHAT PREPARATION IS ALLOWED TO BE. Formatting and redeployment: two operations whose result
does not depend on what the code means. Anything that needed judgement would be the agent
laundering a decision through a flag, so the list is closed and a test holds it closed.

AND IT TOUCHES ONLY THE DECLARED SCOPE. The first version ran `ruff format .` and rewrote
90 files on its first real use, including ones deliberately held on the
`ruff_format.legacy_unformatted` list — a ratchet that only shrinks, quietly emptied by a
convenience. Editing files nobody declared is Rule 2 by another route, so a step that takes
files is given the task's own relevant_files and is SKIPPED, out loud, when there are none.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Step:
    """One preparation command: what it is called, what it runs, why it exists."""

    name: str
    argv: tuple[str, ...]
    because: str
    #: True when the command must be told WHICH files to touch. Such a step is skipped
    #: rather than run tree-wide: a prepare that edits undeclared files is a scope breach
    #: wearing a convenience's clothes.
    takes_files: bool = False
    #: A path that must exist under the root for this step to MEAN anything. Absent, the
    #: step does not apply and is skipped out loud — it has not failed. A project that
    #: installs TAUSIK as a dependency has no `bootstrap/` of its own, and treating that
    #: as a failed preparation would refuse every check it ever ran.
    requires: str | None = None


#: The closed list. Adding to it is a decision about what "preparation" means, so it is
#: made here, in data, where a test can read it — not assembled per run from what looks
#: convenient at the time.
STEPS: tuple[Step, ...] = (
    Step(
        name="ruff format",
        argv=("ruff", "format"),
        because="the ruff_format gate goes red on unformatted files, and formatting is "
        "deterministic — running it is not a judgement about the code",
        takes_files=True,
    ),
    Step(
        name="bootstrap redeploy",
        argv=(sys.executable, "bootstrap/bootstrap.py", "--ide", "all"),
        because="the CLI runs the DEPLOYED copies under .claude/, so an edit under "
        "scripts/ leaves bootstrap_drift red until the profile is rebuilt",
        requires="bootstrap/bootstrap.py",
    ),
)


class PreparationFailed(RuntimeError):
    """A preparation step failed. The run stops here rather than judging an unprepared tree."""


def run(
    root: str | Path, files: Sequence[str] | None = None, *, runner=subprocess.run
) -> list[str]:
    """Run every step in order. Returns one line per step, for the reader and the record.

    `files` is the task's declared scope. A step that takes files and is given none is
    skipped and SAYS so — running it over the whole tree is what rewrote 90 files the first
    time this ran, and silence about a skip reads exactly like success.

    Raises `PreparationFailed` on the first non-zero exit, carrying that step's own output.
    Continuing would run the gates over a tree the agent believes was prepared and was not,
    and a green from that says the opposite of what it seems to say.
    """
    said: list[str] = []
    targets = [f for f in (files or []) if f]
    for step in STEPS:
        if step.requires and not (Path(root) / step.requires).exists():
            said.append(
                f"NOT PREPARED: {step.name} — this tree has no {step.requires}, so the "
                "step does not apply here. It has not failed."
            )
            continue
        if step.takes_files and not targets:
            said.append(
                f"NOT PREPARED: {step.name} — no declared scope to apply it to, and "
                "applying it tree-wide would edit files nobody declared."
            )
            continue
        proc = runner(
            list(step.argv) + (targets if step.takes_files else []),
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            raise PreparationFailed(
                f"preparation step '{step.name}' exited {proc.returncode} — the gates were "
                f"NOT run, because a check over a tree that was not prepared would report "
                f"on something other than what was asked for.\n"
                f"{(proc.stderr or proc.stdout or '').strip()[:2000]}"
            )
        tail = (proc.stdout or "").strip().splitlines()
        said.append(f"PREPARED: {step.name} — {tail[-1] if tail else 'ok'}")
    return said


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
