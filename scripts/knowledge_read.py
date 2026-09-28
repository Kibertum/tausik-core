"""Reading the shared store: labelled, quota'd, and never silently absent.

THREE RULES, each of which exists because the obvious implementation gets it wrong.

LABELLED, USING THE LABEL THAT ALREADY EXISTS. `service_cq_row` established how
this project marks a row that came from somewhere else: `source` states the
provenance, `id` is None because the row has no address HERE, and the title
carries a visible prefix. Shared rows follow it exactly. The `id` matters most:
a shared row does have an id, but in another database, and printing it would
invite `memory show <id>` to return a DIFFERENT, real, local record. A wrong
answer beats no answer only in arguments, never in a knowledge base.

QUOTA'D SEPARATELY, NOT MERGED. The knowledge block runs on hard caps and orders
by `id DESC` as a proxy for recency. The shared store has its OWN id sequence,
so "newer id" across the two means nothing at all. Merging into one quota would
let shared rows silently push project rows out of a block the project depends
on. Shared entries therefore get their own section and their own budget. Note
the precise claim: the PROJECT'S OWN SECTIONS keep their size regardless of how
much has been shared. The block as a whole does grow — it gains a section — and
saying otherwise would be the same overclaim this codebase keeps catching.

NEVER SILENTLY ABSENT — BUT ALSO NOT NAGGING. A store that cannot be read
returns a warning the caller must surface: invisible absence of shared knowledge
is indistinguishable from that knowledge not existing, which is the failure mode
where a person concludes the feature does not work and stops using it. A store
that was never created returns NO warning, because nothing has degraded — the
user simply has not opted in, and warning them every session about a file they
never asked for is how a signal becomes noise.

FTS sanitising is imported from the project search rather than re-written. Two
sanitisers would let one query mean two different things in the two halves of a
single result list, and the difference would show up as "the shared store does
not have it" rather than as a bug.
"""

from __future__ import annotations

import sqlite3
import threading
from typing import Any

from backend_queries import _sanitize_fts5
from knowledge_db import connect_knowledge_db, knowledge_db_exists, knowledge_db_path

GLOBAL_SOURCE = "global"
GLOBAL_LABEL = "[shared]"

# Last degradation notice, set by a read and consumed by whoever renders it.
#
# THREAD-LOCAL, and that is not defensive habit. The MCP server dispatches every
# tool call through `asyncio.to_thread`, so two searches genuinely run in two OS
# threads at once; a module-level global would let one call's warning surface
# beside another call's results, or vanish before its own renderer asked. An
# earlier version of this file asserted the opposite — "produced and rendered
# within one command" — which was true of the CLI and false of the interface
# CLAUDE.md tells agents to prefer.
#
# It also CLEARS on a healthy read rather than only overwriting on a failing
# one. In a long-lived process the difference is the whole guarantee: leaving a
# stale notice in place would attach a past failure to a later, healthy answer.
#
# Lives here rather than on ProjectService because the class-surface ratchet was
# at its cap, and spending a structural budget on a diagnostic would have been
# the wrong trade. Keeping it beside the code that produces it reads better too.
_state = threading.local()


def _remember(warning: str | None) -> str | None:
    _state.warning = warning
    return warning


def pop_last_warning() -> str | None:
    """The last shared-store warning for THIS thread, cleared as it is read."""
    warning = getattr(_state, "warning", None)
    _state.warning = None
    return warning


def _short_origin(origin: str | None) -> str:
    """Last path component only — a no-op on the labels the store now writes.

    `origin_project` holds `basename@fingerprint` since the absolute root stopped
    being stored (see `knowledge_origin`), and a label has no separator, so it
    passes through whole: the display keeps the fingerprint that tells two
    projects called `core` apart. This still shortens because a store may hold
    rows written before that, in the window between opening it read-only and the
    rewrite on the next writable open.
    """
    return (origin or "").rstrip("/\\").replace("\\", "/").rsplit("/", 1)[-1]


def _row(record: sqlite3.Row) -> dict[str, Any]:
    """One shared record shaped like a memory hit — addressless and labelled."""
    return {
        "id": None,
        "source": GLOBAL_SOURCE,
        "type": record["type"],
        "title": f"{GLOBAL_LABEL} {record['title']}",
        "content": record["content"],
        "tags": record["tags"] if "tags" in record.keys() else None,
        "origin_project": _short_origin(record["origin_project"]),
    }


def _open() -> tuple[sqlite3.Connection | None, str | None]:
    """(connection, warning). Absent store is not a warning; unreadable one is."""
    if not knowledge_db_exists():
        return None, None
    try:
        conn = connect_knowledge_db(create=False)
    except (OSError, sqlite3.Error) as e:
        return None, (
            f"Shared knowledge at {knowledge_db_path()} could not be read ({e}); "
            "showing this project only."
        )
    if conn is None:
        # Vanished between the existence check and the open. Rare, but it is a
        # disappearance rather than an absence, so it is not silently equated
        # with "never created".
        return None, (
            f"Shared knowledge at {knowledge_db_path()} disappeared while being "
            "opened; showing this project only."
        )
    return conn, None


def _live_rows(conn: sqlite3.Connection) -> int:
    """Live rows in the shared store — the corpus gate's input.

    Counted rather than estimated because the gate is a threshold: an estimate that reads
    high would switch a provider round-trip on for a corpus too small to benefit, which is
    the exact cost the published numbers say not to pay.
    """
    try:
        return int(
            conn.execute("SELECT COUNT(*) FROM memory WHERE archived_at IS NULL").fetchone()[0]
        )
    except sqlite3.Error:
        return 0


def search_shared_memory(query: str, limit: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    """Shared memory hits for `query`, ranked by FTS relevance then recency.

    The keyword path is the whole answer unless every gate in `semantic_rerank` is open, and
    even then the layer only REORDERS what this query already matched. It asks FTS5 for a
    wider window when a re-rank is possible at all, because reordering a page of five can
    only shuffle five rows that were already going to be shown.
    """
    conn, warning = _open()
    if conn is None:
        return [], _remember(warning)
    try:
        q = _sanitize_fts5(query)
        if not q:
            return [], _remember(None)
        window, prov, corpus = _rerank_window(conn, query, limit)
        rows = conn.execute(
            "SELECT m.* FROM fts_memory f JOIN memory m ON m.id = f.rowid "
            "WHERE fts_memory MATCH ? AND m.archived_at IS NULL "
            "ORDER BY bm25(fts_memory, 10.0, 1.0, 3.0), m.created_at DESC LIMIT ?",
            (q, window),
        ).fetchall()
        hits = [_row(r) for r in rows]
        if window != limit:
            hits = _apply_rerank(query, hits, prov, corpus, limit)
        return hits[:limit], _remember(None)
    except sqlite3.Error as e:
        return [], _remember(
            f"Shared knowledge at {knowledge_db_path()} could not be searched ({e}); "
            "showing this project only."
        )
    finally:
        conn.close()


def _rerank_window(conn: sqlite3.Connection, query: str, limit: int) -> tuple[int, Any, int]:
    """``(window, provider, corpus_rows)`` — how many candidates to ask FTS5 for.

    The window widens ONLY when the layer could actually run. Asking for four times the page
    on every search would make the default path pay for a feature that is switched off, and a
    cost with no benefit is how an optional layer stops being optional.
    """
    try:
        from project_config import load_config
        from semantic_rerank import CANDIDATE_MULTIPLIER, gate, provider_from_config

        prov = provider_from_config(load_config())
        if prov is None:
            return limit, None, 0
        corpus = _live_rows(conn)
        if gate(query, corpus, prov) is not None:
            return limit, prov, corpus
        return limit * CANDIDATE_MULTIPLIER, prov, corpus
    except Exception:  # noqa: BLE001 - a broken optional layer must not break the search
        return limit, None, 0


def _apply_rerank(
    query: str, hits: list[dict[str, Any]], prov: Any, corpus: int, limit: int
) -> list[dict[str, Any]]:
    """Reorder the candidate window, or hand it back untouched.

    Wrapped whole: this is the optional half of a search, and the keyword answer is already in
    hand. Any failure here — an import, a provider, arithmetic — costs the reordering and
    nothing else.
    """
    try:
        from knowledge_db import knowledge_home
        from semantic_rerank import log_decision, rerank

        ordered, decision = rerank(query, hits, prov, corpus, limit)
        log_decision(knowledge_home(), decision)
        return ordered
    except Exception:  # noqa: BLE001 - see docstring
        return hits[:limit]


def _by_type(conn: sqlite3.Connection, mem_type: str, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM memory WHERE type = ? AND archived_at IS NULL "
        "ORDER BY created_at DESC, id DESC LIMIT ?",
        (mem_type, limit),
    ).fetchall()


def shared_memory_by_type(mem_type: str, limit: int) -> tuple[list[dict[str, Any]], str | None]:
    """Most recent shared entries of one type. Standalone; opens its own handle."""
    conn, warning = _open()
    if conn is None:
        return [], _remember(warning)
    try:
        return [_row(r) for r in _by_type(conn, mem_type, limit)], _remember(None)
    except sqlite3.Error as e:
        return [], _remember(
            f"Shared knowledge could not be read ({e}); showing this project only."
        )
    finally:
        conn.close()


def shared_decisions(limit: int) -> tuple[list[dict[str, Any]], str | None]:
    """Most recent shared decisions. Standalone; opens its own handle."""
    conn, warning = _open()
    if conn is None:
        return [], _remember(warning)
    try:
        return [_decision_row(r) for r in _decisions(conn, limit)], _remember(None)
    except sqlite3.Error as e:
        return [], _remember(
            f"Shared knowledge could not be read ({e}); showing this project only."
        )
    finally:
        conn.close()


def _decisions(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM decisions ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()


def _decision_row(record: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": None,
        "source": GLOBAL_SOURCE,
        "decision": f"{GLOBAL_LABEL} {record['decision']}",
        "rationale": record["rationale"],
        "origin_project": _short_origin(record["origin_project"]),
    }


BLOCK_TYPES = ("convention", "gotcha", "pattern")


def read_shared_block(max_shared: int) -> tuple[list[tuple[str, str]], str | None]:
    """Everything the knowledge block needs, over ONE connection.

    The four queries used to open, initialise and close the store four separate
    times, and this runs on every session start and every CLAUDE.md refresh —
    four full schema scripts where one handle does. Batching them is not a
    micro-optimisation; it is the difference between a hot path touching the
    file once and touching it four times.

    Returns (entries, warning) where each entry is (kind, text).
    """
    conn, warning = _open()
    if conn is None:
        return [], _remember(warning)
    try:
        entries: list[tuple[str, str]] = [
            ("decision", r["decision"]) for r in _decisions(conn, max_shared)
        ]
        for mem_type in BLOCK_TYPES:
            entries.extend((mem_type, r["title"]) for r in _by_type(conn, mem_type, max_shared))
        return entries, _remember(None)
    except sqlite3.Error as e:
        return [], _remember(
            f"Shared knowledge could not be read ({e}); showing this project only."
        )
    finally:
        conn.close()
