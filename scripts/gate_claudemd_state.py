"""CLAUDE.md state gate — refuses a block that was NOT generated from this DB.

claudemd-drift-gates-do-not-notice-an-emptied-dynamic-block. The DYNAMIC section
of CLAUDE.md (and its AGENTS.md sibling) is the first thing a fresh agent reads
and the only thing it reads GUARANTEED. It claims to be a rendering of this
project's database. Nothing checked that claim, and the cost is measured, not
feared: the block has been overwritten with the shape of an EMPTY project
("Tasks: 0/1 done, 0 active, 0 blocked", memory tail gone) and that wipe reached
TWENTY commits between the v1.0.0 release (2026-04-10) and 2026-08-26 — through
v1.2.0, v1.3.x, v1.4.0 and v1.7.0. Three full green suites, three signed verify
receipts and three QG-2 closes passed over the live corruption without a word.

A wiped block does not look like a failure. It looks like a young project: the
agent gets no error, it gets WRONG CONTEXT and works from it confidently. That is
the same class as "five mechanisms silently write ZERO instead of an error"
(docs/ru/sessions.md:64-76), and it is why this gate BLOCKS rather than warns.

WHAT IS COMPARED, AND WHY IT IS ONLY THIS. Staleness is legitimate: the block is
refreshed at checkpoint/session-end, so between refreshes its counters lag the DB
by whatever the session has closed. A gate that reds on that would be switched
off the first day it shipped, so the counters are NOT compared — any comparison
of them needs a tolerance, and a tolerance is a number nobody can defend.

The memory tail is different, and that difference is the whole gate: it is a
BOOLEAN fact that staleness cannot flip. A block rendered from a database that
holds knowledge ALWAYS carries a tail, whenever it was rendered. A block with no
tail while the live DB has knowledge was not rendered from this database at all —
it came from another one (in the observed defect, a temporary project's empty DB
written to the repository's path). No threshold, no tuning, no list to maintain.

WHY GIT HISTORY IS NOT THE ARBITER HERE, AGAINST CONVENTION #424. The first draft
accepted any `Tasks:` line that ever appeared in the file's git history and
reddened on strangers. That plan was killed by measurement: the corrupted line IS
in the history — ten times in CLAUDE.md alone. History works as a false-positive
filter when the history is clean by construction; this artifact rotted inside the
history itself, so the filter would have whitelisted exactly the defect it was
hired to catch.

WHY IT ASKS INSTEAD OF MODELLING (dead end #427). Paths come from the writer's own
resolvers (`claudemd_state.resolve_claudemd`, `claudemd_writer.resolve_sibling_targets`)
and the markers from the writer's own constants, so the gate looks exactly where
the writer writes; "does the project have knowledge" is answered by the producer
of the tail itself. The gate keeps no file list, no SQL and no copy of the format.

Read-only and fail-open: a gate must never crash the commit it guards.
"""

from __future__ import annotations

import os

# The writer's own markers, imported rather than copied: a guard that carries its
# own idea of where the block starts is a second source of truth, and this file
# exists because the first one was never checked. See the module docstring.
from claudemd_writer import _MARKER_END, _MARKER_START


def extract_dynamic_block(text: str) -> str | None:
    """The text BETWEEN the DYNAMIC markers, or ``None`` when there is no block.

    ``None`` means "nothing to judge" (an un-managed file), not "clean" — the
    caller skips such a file rather than counting it as a pass. END is located
    strictly AFTER START, the same way the writer slices it, so a marker quoted
    earlier in body text cannot mis-slice the block.
    """
    start_at = text.find(_MARKER_START)
    if start_at == -1:
        return None
    body_at = start_at + len(_MARKER_START)
    end_at = text.find(_MARKER_END, body_at)
    return text[body_at:] if end_at == -1 else text[body_at:end_at]


def block_carries_memory_tail(block: str, sentinel: str) -> bool:
    """True iff `block` carries a memory tail with at least one item under it.

    `sentinel` is the tail's own first line as produced by
    `build_compact_memory_tail` — passed in rather than hard-coded so a rename in
    the producer moves this check with it instead of silently blinding it.

    A header with nothing under it is NOT a tail: the failure this gate exists for
    empties the section, and an empty section carries exactly as little context as
    a missing one.
    """
    lines = block.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != sentinel.strip():
            continue
        return any(rest.strip() for rest in lines[i + 1 :])
    return False


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def run_claudemd_state_gate_for(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Registry-uniform ``(gate, files)`` entrypoint (gate-registry-single-source).

    Both arguments are ignored, as in gate_state_roundtrip: the artifact under
    check is the repository's own CLAUDE.md, which is not in any task's declared
    files — and narrowing to those files is precisely how this went unnoticed for
    four months (convention #421: a name-based selection cannot see a gate that
    concerns the whole tree).
    """
    return run_claudemd_state_gate()


def run_claudemd_state_gate() -> tuple[bool, str]:
    """Fail iff an agent-instruction file's DYNAMIC block has no memory tail
    while the live database has knowledge to render.

    Returns ``(passed, message)``. Passes (skips) when there is nothing to judge:
    no `.tausik/`, no database, no CLAUDE.md, no DYNAMIC markers, or a knowledge
    base that is genuinely empty — a project with no memory has no tail owed to
    it, and inventing a red there would punish a fresh clone for being fresh.
    """
    try:
        from project_config import find_tausik_dir

        tausik_dir = os.path.abspath(find_tausik_dir())
        project_root = os.path.dirname(tausik_dir)
        db_path = os.path.join(tausik_dir, "tausik.db")
        if not os.path.isfile(db_path):
            return True, "No tausik.db — CLAUDE.md dynamic-state check skipped."
    except Exception as e:  # noqa: BLE001 — a gate must never crash the commit
        return True, f"CLAUDE.md dynamic-state check unavailable ({type(e).__name__}: {e})."

    be = None
    try:
        from claudemd_state import resolve_claudemd
        from claudemd_writer import resolve_sibling_targets
        from project_backend import SQLiteBackend
        from service_knowledge_aggregates import build_compact_memory_tail

        primary = resolve_claudemd(project_root)
        if primary is None:
            return True, "No CLAUDE.md — dynamic-state check skipped."

        be = SQLiteBackend(db_path)
        tail = build_compact_memory_tail(be)
        if not tail:
            return True, (
                "The knowledge base is empty — the dynamic block owes no memory "
                "tail, nothing to compare."
            )
        sentinel = tail[0]

        offenders: list[str] = []
        judged: list[str] = []
        for path in resolve_sibling_targets(primary):
            text = _read(path)
            if text is None:
                continue
            block = extract_dynamic_block(text)
            if block is None:
                continue
            judged.append(path)
            if not block_carries_memory_tail(block, sentinel):
                offenders.append(path)
    except Exception as e:  # noqa: BLE001 — fail-open: never block a commit on an internal fault
        return True, f"CLAUDE.md dynamic-state check unavailable ({type(e).__name__}: {e})."
    finally:
        if be is not None:
            try:
                be.close()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass

    if not judged:
        return True, "No DYNAMIC block in any agent-instruction file — check skipped."

    if offenders:
        names = "\n  ".join(os.path.relpath(p, project_root) for p in offenders)
        return False, (
            f"CLAUDE.md state drift: {len(offenders)} of {len(judged)} agent-instruction "
            "file(s) carry a DYNAMIC block with NO memory tail while this project's "
            f"database has knowledge to render:\n  {names}\n"
            "That block was not generated from this database — it describes an empty "
            "or foreign project, and the next agent will read it as the truth about "
            "this one.\n"
            "Fix: tausik update-claudemd   (re-renders the block from the live DB)."
        )
    return True, (
        f"CLAUDE.md dynamic block carries the memory tail in {len(judged)} file(s) — "
        "generated from this database."
    )
