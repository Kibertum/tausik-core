#!/usr/bin/env python3
"""What a write gate is ALLOWED TO DECIDE, in one place per question.

Split out of `_common` when it crossed the file-size cap, but the seam is not
arbitrary: everything here answers a POLICY question that more than one gate
asks, and every one of these questions was previously answered separately by
each gate — with measured disagreement each time.

  * `classify_target` — is this file ours? `task_gate` and `scope_write_gate`
    computed containment apart and gave OPPOSITE answers for a path on another
    drive, so one refused a write the other allowed.
  * `fail_open_on_db_error` — may a gate that cannot read the DB let the write
    through? Three gates read the environment themselves; the answer is now
    given once, and it changed in 1.9 (see the function).

A policy each caller re-derives is a policy that differs between callers, and
the difference shows up as a gate that can be walked around rather than as an
error.
"""

from __future__ import annotations

import os

#: Legacy name for the opt-in that has become the default. Kept only to be
#: RECOGNISED and reported — never to change behaviour.
_LEGACY_FAIL_SECURE = "TAUSIK_HOOK_FAIL_SECURE"
_FAIL_OPEN = "TAUSIK_HOOK_FAIL_OPEN"


def fail_open_on_db_error() -> bool:
    """Whether a gate that CANNOT read the DB should let the write through.

    THE DEFAULT IS NOW "NO", AND THAT IS A BREAKING CHANGE. It was announced as
    one, publicly, to an external contributor on PR #5, and it was the stated
    reason their work waited for 1.9 instead of a patch release: "task_gate
    becomes fail-secure by default and TAUSIK_HOOK_FAIL_SECURE=1 is replaced by
    its inverse TAUSIK_HOOK_FAIL_OPEN=1". The merits were agreed there too — a
    guard that cannot evaluate should refuse, not wave the edit through, which
    is what this project already argues for QG-0 and QG-2. `task_gate` was the
    exception that contradicted it.

    The escape hatch is real and deliberate: a corrupt or locked database must
    not leave someone unable to edit anything, so `TAUSIK_HOOK_FAIL_OPEN=1`
    restores the old behaviour for whoever needs it. What changed is which side
    you have to ask for.

    ONE ANSWER FOR THREE GATES. `task_gate`, `scope_write_gate` and
    `bash_write_gate` each read the environment themselves, which is how a
    policy comes to differ between the channels enforcing it — measured twice
    already in this codebase, on transaction ownership and on write
    jurisdiction. They ask this function instead.
    """
    return bool(os.environ.get(_FAIL_OPEN))


def legacy_fail_secure_notice() -> str:
    """A line to print when the RETIRED variable is set, or "" when it is not.

    Setting it is now a no-op, because it asks for what already happens. A
    no-op that says nothing is the silent kind of wrong this project refuses
    elsewhere: someone configured a safety control and would never learn that
    the name stopped meaning anything.
    """
    if not os.environ.get(_LEGACY_FAIL_SECURE):
        return ""
    return (
        f"NOTE: {_LEGACY_FAIL_SECURE} is set and no longer does anything — refusing on a "
        f"DB error is the DEFAULT now. Unset it; to restore the old behaviour use "
        f"{_FAIL_OPEN}=1."
    )


def classify_target(
    file_path: str, project_dir: str, *, cwd: str | None = None
) -> tuple[str, str | None]:
    """Where a write lands relative to this project: the ONE answer both gates use.

    Returns ``(verdict, rel)`` with verdict one of:
      * ``"inside"``  -- ``rel`` is the project-relative path;
      * ``"outside"`` -- PROVEN to sit outside this project; ``rel`` is None;
      * ``"unknown"`` -- could not be decided; ``rel`` is None.

    "outside" and "unknown" are separated on purpose, because the two gates
    that ask this question want opposite things from them: a target proven
    outside is not this project's business, while one we could not classify
    must stay gated. Collapsing them is exactly the bug this function replaces.

    THIS USED TO BE TWO FUNCTIONS THAT DISAGREED. `task_gate` decided with
    `commonpath` and read any exception as "not proven outside" -> keep gating;
    `scope_write_gate` decided with `relpath` and read `(OSError, ValueError)`
    as "outside" -> allow. On Windows BOTH raise `ValueError` for paths on
    different drives, so one and the same target was refused by the Write gate
    and accepted by the Bash gate that reuses `scope_write_gate`. Measured
    live: a scratch file under `C:\\...\\Temp` was blocked via Write and
    written via a Bash heredoc, one call later. A gate cheaper to bypass than
    to satisfy stops being a gate.

    A DIFFERENT DRIVE IS PROOF, NOT DOUBT. Containment across drives is
    impossible by construction, so that case answers "outside" -- the strongest
    evidence available, previously handled as the weakest.

    Containment is decided on realpath, and by comparing path PARTS rather than
    with `startswith`: a sibling sharing a prefix (``…/core-old`` next to
    ``…/core``) reads as inside under a plain prefix test, and a symlink
    pointing from outside into the project reads as outside -- each the wrong
    answer in the dangerous direction. Anything that still raises is "unknown",
    which keeps the gate on.
    """
    try:
        base = cwd if isinstance(cwd, str) and cwd else project_dir
        target = os.path.realpath(os.path.join(base, os.path.expanduser(file_path)))
        root = os.path.realpath(project_dir)
    except (OSError, ValueError):
        return ("unknown", None)
    target_drive, root_drive = os.path.splitdrive(target)[0], os.path.splitdrive(root)[0]
    if target_drive.lower() != root_drive.lower():
        return ("outside", None)
    try:
        rel = os.path.relpath(target, root)
    except (OSError, ValueError):
        return ("unknown", None)
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        return ("outside", None)
    return ("inside", rel)
