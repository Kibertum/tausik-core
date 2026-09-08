"""Answering "what do I read to change this" in twenty lines instead of five files.

MEASURED BEFORE THIS EXISTED (session #236, on the live graph). An unranked
neighbour list is not an answer:

    scripts/verify_scope_honesty.py    42 neighbours, 2,881 KB of files
    scripts/gate_test_resolver.py      38 neighbours, 2,779 KB
    scripts/service_artifact_graph.py  29 neighbours, 2,610 KB

An agent handed that reads all of it and spends MORE than the grep this was
supposed to replace. So the answer is RANKED and CUT to a budget, and the cut is
stated. Completeness is not the goal here; it is the failure mode.

RANK COMES FROM PROVENANCE, not from one blended number. What a test RUN
observed outranks what a person declared, which outranks what git noticed
happening together — because that is the order in which the three are likely to
be about this change rather than about some other one. Within a layer, the
observation count decides.

EVERY LINE SAYS WHY. A ranked list without reasons is indistinguishable from an
arbitrary one, and an agent cannot tell a strong entry from a weak one to stop
reading early — which is the whole saving.

ABSENCE IS VISIBLE. A path the graph does not know returns "I do not know" and
the command that would fix it, never an empty list: an empty list reads as "this
file is related to nothing", and that is a confident wrong answer.
"""

from __future__ import annotations

import os
import sqlite3

#: How many neighbours an answer carries before it states the remainder. Twelve
#: is the same bound `tausik symbol` and `graph show` use, for the same reason:
#: past it the answer stops being cheaper than reading the files.
DEFAULT_BUDGET = 12

#: Layer -> (rank, how to say it). Rank orders the answer; the phrase is what
#: makes each line self-explaining.
_LAYER_RANK: dict[str, tuple[int, str]] = {
    "observed_coverage": (0, "a test run reached it"),
    "declared_crosscutting": (1, "a test names it in CROSSCUTTING_SCOPE"),
    "declared_relevant_files": (2, "worked on together in one task"),
    "declared_scope_paths": (3, "inside one task's declared scope"),
    "declared_renar": (4, "linked by a RENAR artifact"),
    "git_cochange": (5, "changed together in git history"),
}

_UNKNOWN_RANK = (9, "related, provenance unrecognised")


def _db(project_dir: str) -> str:
    return os.path.join(project_dir, ".tausik", "tausik.db")


def _rows(project_dir: str, path: str, direction: str) -> list[tuple[str, str, int]]:
    """(other path, layer, observations) for the edges this question needs.

    TWO QUESTIONS, AND THEY ARE NOT MIRROR IMAGES — because this graph has no
    direction of dependency and says so (see `docs/*/graph.md`). Co-change is
    symmetric: git saw two files move together and cannot say which followed
    which. A declared grouping is symmetric too. Only `covers` is directional,
    because a test reaching code is not the same as code reaching a test.

    So:

      "read"    — every neighbour, BOTH directions unioned. Storing a symmetric
                  edge picks a side arbitrarily (the pair is sorted), and asking
                  one side would drop most of the answer: on this repository the
                  out-direction alone returned 2 of 42 neighbours.
      "affects" — only the tests whose `covers` edge points AT this file. That
                  question has a real answer, and it is the one worth asking
                  before an edit: what will go red.
    """
    db = _db(project_dir)
    if not os.path.isfile(db):
        return []
    if direction == "affects":
        sql = (
            "SELECT s.path, e.layer, e.observations FROM artifact_edges e "
            "JOIN artifacts s ON s.id = e.source_artifact_id "
            "JOIN artifacts d ON d.id = e.target_artifact_id "
            "WHERE d.path = ? AND e.relation = 'covers'"
        )
        params: tuple[str, ...] = (path,)
    else:
        sql = (
            "SELECT d.path, e.layer, e.observations FROM artifact_edges e "
            "JOIN artifacts s ON s.id = e.source_artifact_id "
            "JOIN artifacts d ON d.id = e.target_artifact_id WHERE s.path = ? "
            "UNION ALL "
            "SELECT s.path, e.layer, e.observations FROM artifact_edges e "
            "JOIN artifacts s ON s.id = e.source_artifact_id "
            "JOIN artifacts d ON d.id = e.target_artifact_id WHERE d.path = ?"
        )
        params = (path, path)
    try:
        with sqlite3.connect(db, timeout=2) as conn:
            return [
                (str(r[0]), str(r[1]), int(r[2] or 1))
                for r in conn.execute(sql, params).fetchall()
                if str(r[0]) != path
            ]
    except sqlite3.Error:
        return []


def is_known(project_dir: str, path: str) -> bool:
    db = _db(project_dir)
    if not os.path.isfile(db):
        return False
    try:
        with sqlite3.connect(db, timeout=2) as conn:
            row = conn.execute("SELECT 1 FROM artifacts WHERE path = ?", (path,)).fetchone()
    except sqlite3.Error:
        return False
    return row is not None


def graph_is_empty(project_dir: str) -> bool:
    db = _db(project_dir)
    if not os.path.isfile(db):
        return True
    try:
        with sqlite3.connect(db, timeout=2) as conn:
            row = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()
    except sqlite3.Error:
        return True
    return not row or not row[0]


def rank(rows: list[tuple[str, str, int]]) -> list[tuple[str, str, int, str]]:
    """(path, layer, observations, reason), strongest evidence first.

    One entry per PATH: the strongest layer wins, because two lines about the
    same file spend the reader's budget twice to say one thing. The observation
    count of the winning layer is what survives.
    """
    best: dict[str, tuple[int, str, int]] = {}
    for path, layer, observations in rows:
        rank_value = _LAYER_RANK.get(layer, _UNKNOWN_RANK)[0]
        current = best.get(path)
        if current is None or (rank_value, -observations) < (current[0], -current[2]):
            best[path] = (rank_value, layer, observations)
    ordered = sorted(best.items(), key=lambda kv: (kv[1][0], -kv[1][2], kv[0]))
    return [
        (path, layer, observations, _LAYER_RANK.get(layer, _UNKNOWN_RANK)[1])
        for path, (_r, layer, observations) in ordered
    ]


def answer(
    project_dir: str, path: str, *, direction: str = "read", budget: int = DEFAULT_BUDGET
) -> str:
    """The navigation answer for one path, ranked, cut, and self-explaining."""
    normalised = path.replace("\\", "/")

    if graph_is_empty(project_dir):
        return (
            f"the graph is empty, so nothing is known about {normalised} — "
            "run `tausik graph build` first"
        )
    if not is_known(project_dir, normalised):
        # ABSENCE, VISIBLE. An empty list here would read as "this file relates
        # to nothing", which is a confident wrong answer rather than a missing
        # one, and the reader would act on it.
        return (
            f"{normalised} is NOT in the graph — this is 'unknown', not 'unrelated'. "
            "Either the path is wrong, it is outside this project's source roots, "
            "or the graph has not been rebuilt since the file appeared "
            "(`tausik graph build`)."
        )

    ranked = rank(_rows(project_dir, normalised, direction))
    if not ranked:
        if direction == "affects":
            return (
                f"no test is OBSERVED to cover {normalised}. That is 'not observed', "
                "not 'not covered' — a test exercising it in a SUBPROCESS is invisible "
                "to the observer, and the graph may simply not have been fed a run yet."
            )
        return (
            f"{normalised} is in the graph and has no edges yet. Nothing has been "
            "observed, declared or seen changing alongside it."
        )

    heading = (
        f"to change {normalised}, read these first:"
        if direction != "affects"
        else f"changing {normalised} should turn these red first:"
    )
    lines = [heading]
    for entry_path, _layer, observations, reason in ranked[:budget]:
        seen = f" x{observations}" if observations > 1 else ""
        lines.append(f"  {entry_path}  — {reason}{seen}")
    if len(ranked) > budget:
        # The cut is NAMED. A silently truncated answer teaches the reader to go
        # and read everything anyway, which costs both.
        lines.append(
            f"  ... {len(ranked) - budget} weaker link(s) not shown "
            f"(strongest {budget} listed; raise with --limit)"
        )
    return "\n".join(lines)
