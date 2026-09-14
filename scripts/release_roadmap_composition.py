"""Reading the release composition out of the decision journal.

Split from `release_roadmap` (the renderer) when the explicit «Состав:» line
arrived and pushed the generator past the filesize gate. Everything here is a
READ of the owner's record: which stories are in the release, which decision
chartered it, and which trajectory it recorded. Nothing here writes, and
nothing here reads the clock — see `release_roadmap` for why that matters.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from tausik_utils import ServiceError

#: A decision that names this many of the release stories is making a statement
#: ABOUT THE COMPOSITION. One story is a decision about that story; two or more
#: is a list. The threshold is what separates the two, and it is the only reason
#: an ordinary per-story decision does not get mistaken for a scope declaration.
COMPOSITION_MIN_STORIES = 2

_VERSION_RE = re.compile(r"\d+\.\d+")
_DECISION_REF_RE = re.compile(r"#(\d+)")
_POINTS_RE = re.compile(r"(?:Точки|Points)\s*:\s*([\d]+(?:\s*,\s*[\d]+)*)")

#: An EXPLICIT composition line inside a decision — «Состав: a, b, c» — and an
#: explicit charter reference — «Устав: #N». These exist because inferring the
#: composition from prose failed on the live journal: decision #363 answered
#: three owner questions and happened to mention three story slugs, and the
#: inference read it as a full restatement, shrinking the release from thirteen
#: stories to three while the same map quoted #360 — which names ten of them —
#: as the charter. Nothing reddened: the freshness guard compares the file to
#: the generator, and the generator was faithfully wrong. A composition is a
#: declaration, so it is READ from a line written as one; once any decision
#: carries the line, prose that merely mentions two slugs no longer restates
#: the release. The inference stays only as the fallback for a journal that has
#: never written the line, and the map says which of the two it used.
#: The list ends at the line, a full stop or a semicolon: slugs are kebab-case
#: and carry none of those, so a sentence continuing after the list cannot be
#: read as one more story — and a list broken by prose («a, b и c») surfaces as
#: an unknown slug, loudly, rather than as a shorter release.
_COMPOSITION_RE = re.compile(r"(?:Состав|Composition)\s*:\s*([^\n.;]*)", re.IGNORECASE)
_CHARTER_RE = re.compile(r"(?:Устав|Charter)\s*:\s*#(\d+)", re.IGNORECASE)


class RoadmapUnreadable(ServiceError):
    """The release composition could not be read. Not the same as "empty"."""


def _stories(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    cur = conn.execute(
        "SELECT s.id, s.slug, s.title, s.status, e.slug AS epic_slug, "
        "e.title AS epic_title FROM stories s JOIN epics e ON s.epic_id = e.id"
    )
    cols = [c[0] for c in cur.description]
    return {row[1]: dict(zip(cols, row)) for row in cur.fetchall()}


def _decisions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every decision, oldest first, as plain dicts."""
    cur = conn.execute("SELECT id, decision, created_at FROM decisions ORDER BY id ASC")
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _named_stories(text: str, known: dict[str, dict[str, Any]]) -> list[str]:
    """Story slugs a decision names, in the order the decision names them.

    The order is the owner's: a scope decision lists the stories in the order it
    considers them, and re-sorting that alphabetically would substitute my
    ordering for theirs in a document whose subject is their plan.
    """
    hits = [(text.index(slug), slug) for slug in known if slug in text]
    hits.sort()
    return [slug for _, slug in hits]


def _declared(
    decisions: list[dict[str, Any]], known: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any] | None, list[str]]:
    """The newest decision carrying an explicit «Состав:» line, and its slugs.

    Every slug on the line must be a story that exists: a typo would otherwise
    drop a story from the release silently, which is the exact failure the line
    was introduced to end. An empty line is refused for the same reason — it is
    not "a release with nothing in it", it is a declaration nobody finished.
    A repeated slug is refused too: it would render twice and double-count the
    totals. ONE slug is accepted — the two-story minimum of the inference exists
    to tell a mention from a declaration, and a line written as a declaration
    needs no such tell.
    """
    for row in reversed(decisions):
        m = _COMPOSITION_RE.search(row["decision"] or "")
        if m is None:
            continue
        slugs = [s.strip().strip("`") for s in m.group(1).split(",")]
        slugs = [s for s in slugs if s]
        if not slugs:
            raise RoadmapUnreadable(
                f"decision #{row['id']} carries an empty composition line; a "
                "declared release with no stories is a declaration nobody "
                "finished, not an empty release"
            )
        repeated = sorted({s for s in slugs if slugs.count(s) > 1})
        if repeated:
            raise RoadmapUnreadable(
                f"decision #{row['id']} declares a composition naming "
                f"{', '.join(repeated)} more than once; a repeated story would "
                "render twice and double-count the totals"
            )
        unknown = [s for s in slugs if s not in known]
        if unknown:
            raise RoadmapUnreadable(
                f"decision #{row['id']} declares a composition naming "
                f"{', '.join(unknown)}, and no such story exists; a slug that "
                "resolves to nothing would drop a story from the release silently"
            )
        return row, slugs
    return None, []


def _inferred(
    decisions: list[dict[str, Any]], known: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any] | None, list[str]]:
    """The legacy reading: the newest decision that MENTIONS two or more stories.

    Kept only for a journal that has never written a «Состав:» line. On this
    project's own journal it read an additive answer as a restatement; the map
    names which reading it used so the reader knows how much to trust it.
    """
    for row in reversed(decisions):
        named = _named_stories(row["decision"] or "", known)
        if len(named) >= COMPOSITION_MIN_STORIES:
            return row, named
    return None, []


def composition(conn: sqlite3.Connection) -> dict[str, Any]:
    """The release composition in force, read out of the decisions.

    The newest decision that DECLARES a composition («Состав:») wins; while no
    decision has ever declared one, the newest decision mentioning two or more
    stories stands in. Scope is restated every shift, and the last statement is
    the one that holds. Raises rather than returning an empty composition — see
    the module docstring.
    """
    known = _stories(conn)
    decisions = _decisions(conn)
    basis, slugs = _declared(decisions, known)
    declared = basis is not None
    if basis is None:
        basis, slugs = _inferred(decisions, known)
    if basis is None:
        raise RoadmapUnreadable(
            "no decision names two or more stories, so the release composition "
            "is undeclared; refusing to publish a roadmap that would look like "
            "a release with no stories in it"
        )
    charter = _charter(decisions, slugs, known, basis)
    version = _VERSION_RE.search(basis["decision"] or "")
    return {
        "basis": basis,
        "charter": charter,
        "declared": declared,
        "stories": [known[s] for s in slugs],
        "version": version.group(0) if version else None,
        "points": _points(basis["decision"] or ""),
    }


def _charter(
    decisions: list[dict[str, Any]],
    slugs: list[str],
    known: dict[str, dict[str, Any]],
    basis: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """The decision that defined the release, found by following the record.

    A basis that names its charter outright («Устав: #N») is believed when #N
    is a decision other than itself. Otherwise the EARLIEST decision naming this
    composition is the one that fixed it, and it cites the charter by number in
    its own text — so the link is read, not assumed. If that number resolves to
    no decision, the finder returns the earliest composition decision itself
    rather than inventing a reference.
    """
    scope = {s: known[s] for s in slugs}
    by_id = {d["id"]: d for d in decisions}
    if basis is not None:
        m = _CHARTER_RE.search(basis["decision"] or "")
        if m is not None:
            target = by_id.get(int(m.group(1)))
            if target is not None and target["id"] != basis["id"]:
                return target
    for row in decisions:
        if len(_named_stories(row["decision"] or "", scope)) < COMPOSITION_MIN_STORIES:
            continue
        for ref in _DECISION_REF_RE.findall(row["decision"] or ""):
            target = by_id.get(int(ref))
            if target is not None and target["id"] != row["id"]:
                return target
        return row
    return None


def _points(text: str) -> list[str] | None:
    """The scope trajectory a decision recorded, or None when it recorded none.

    None is not []: a decision that never wrote the line and a decision that
    wrote an empty one are different states, and a reader of the map must be
    able to tell "no trajectory was recorded" from "the trajectory is empty".
    """
    m = _POINTS_RE.search(text)
    if not m:
        return None
    return [p.strip() for p in m.group(1).split(",") if p.strip()]
