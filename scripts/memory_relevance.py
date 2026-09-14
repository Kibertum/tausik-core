"""Memory pulled back into the window by what the task is ABOUT, not by when it was written.

Anthropic's guidance for long-running agents: structured notes live outside
the context window and are pulled back in at the moment they matter. TAUSIK
had the storing half — 431 memory rows at the time of writing — and only a
recency tail for the pulling half: the newest five per type, whatever the task.
Measured in session #189: the two rows that mattered that day — #425, the
retirement of the "five names" rule, and #428, "a signed receipt is not a
passing commit" — were carried into the prompt BY HAND, because the recency
tail could not have returned them.

WHAT DECIDES RELEVANCE. The task's own declaration: its title and slug, the
stems and path segments of `relevant_files` and `scope_paths`, its story, and
the tags of decisions linked to it. Those become one FTS5 query with OR
semantics over the memory table, ranked by bm25 — FTS5 is already there, no
embeddings. `backend.memory_search` is implicit AND and stays untouched; this
module asks the backend for the OR form.

WHAT AN EMPTY ANSWER MUST SAY. "Relevant memory: none matched <terms>", with
the terms listed. Silence would be read as "no memory on this topic", which is
the exact misreading this module exists to end. A failing FTS query degrades to
the same named line — never to a crash of `task start`.

WHAT THIS DOES NOT REPLACE. The recency tail in CLAUDE.md is the core and stays;
relevance is pulled in on top of it, at `task start`, on resume and in
`task show`.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, NamedTuple

from backend_queries import _FTS5_TOKEN_SPECIAL_RE
from memory_supersedes import as_int, superseder_of

MAX_ENTRIES = 8
MAX_TERMS = 24
MIN_TERM_LEN = 3

# Words that name nothing about a subject: they would match half the store.
_STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "not",
        "with",
        "from",
        "into",
        "that",
        "this",
        "when",
        "are",
        "was",
        "its",
        "has",
        "have",
        "does",
        "only",
        "than",
        "then",
        "more",
        "scripts",
        "docs",
        "tausik",
        "tasks",
        "stories",
        "task",
        "py",
        "md",
        "json",
        "yaml",
        "yml",
        "src",
        "lib",
        "или",
        "для",
        "что",
        "как",
        "это",
        "при",
        "без",
        "над",
        "под",
        "его",
        "она",
    }
)
_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9]{%d,}" % MIN_TERM_LEN)


class Relevance(NamedTuple):
    entries: list[dict[str, Any]]  # live memory rows, bm25 order, with `_matched` terms
    terms: list[str]  # the query that was tried, for the named-empty line
    error: str | None  # set when the search itself failed; entries is then empty


def _words(text: str | None) -> list[str]:
    if not text:
        return []
    return [w.lower() for w in _WORD.findall(text)]


def _as_list(value: Any) -> list[Any]:
    """Task rows carry list fields as JSON text; a caller may hand a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip().startswith("["):
        try:
            loaded = json.loads(value)
        except ValueError:
            return []
        return loaded if isinstance(loaded, list) else []
    return []


def _path_terms(paths: Any) -> list[str]:
    out: list[str] = []
    paths = _as_list(paths)
    if not paths:
        return out
    for raw in paths:
        if not isinstance(raw, str):
            continue
        stem = os.path.splitext(os.path.basename(raw))[0]
        out.extend(_words(stem.replace("_", " ").replace("-", " ")))
        for seg in raw.replace("\\", "/").split("/")[:-1]:
            out.extend(_words(seg.replace("_", " ").replace("-", " ")))
    return out


def task_terms(task: dict[str, Any], decisions: list[dict[str, Any]] | None = None) -> list[str]:
    """The term set a task declares about itself — ordered, de-duplicated, bounded.

    Title words come first (the strongest signal), then slug parts, then the
    declared files, then story and linked-decision tags. Bounded at MAX_TERMS
    so a task with forty files does not become a query that matches everything.
    """
    seen: set[str] = set()
    ordered: list[str] = []

    def add(words: list[str]) -> None:
        for w in words:
            if w in _STOP or w in seen or w.isdigit():
                continue
            seen.add(w)
            ordered.append(w)

    add(_words(task.get("title")))
    add(_words((task.get("slug") or "").replace("-", " ")))
    add(_path_terms(task.get("relevant_files")))
    add(_path_terms(task.get("scope_paths")))
    add(_words((task.get("story_slug") or task.get("story") or "").replace("-", " ")))
    for d in decisions or []:
        add(_words(" ".join(str(t) for t in _as_list(d.get("tags"))) or str(d.get("tags") or "").replace(",", " ")))
    return ordered[:MAX_TERMS]


def search_any(be: Any, terms: list[str], n: int = 24) -> list[dict[str, Any]]:
    """Rows matching ANY of `terms`, best bm25 first — the relevance form.

    `backend.memory_search` joins bare tokens with FTS5's implicit AND, which
    is right for a person typing a query and wrong for a task's term set: a
    task naming twelve files matches nothing under AND. Each term is quoted on
    its own (so hyphens and dots cannot become operators) and joined with OR; a
    term that matches nothing simply contributes nothing. Archived rows are
    never relevant. Lives here rather than on the backend class on purpose: the
    class-surface ratchet lets the two god classes only shrink.
    """
    quoted = []
    for term in terms:
        clean = _FTS5_TOKEN_SPECIAL_RE.sub(" ", str(term)).strip()
        if clean:
            quoted.append(f'"{clean}"')
    if not quoted:
        return []
    sql = (
        "SELECT m.* FROM memory m JOIN fts_memory f ON m.id=f.rowid "
        "WHERE fts_memory MATCH ? AND m.archived_at IS NULL "
        "ORDER BY bm25(fts_memory, 10.0, 1.0, 3.0) LIMIT ?"
    )
    rows: list[dict[str, Any]] = be._q(sql, (" OR ".join(quoted), n))
    return rows


def _tags_text(row: dict[str, Any]) -> str:
    return " ".join(str(t) for t in _as_list(row.get("tags"))).lower() or str(row.get("tags") or "").lower()


def _score(row: dict[str, Any], terms: list[str]) -> tuple[float, list[str]]:
    """Distinct matched terms, weighted by WHERE they match: a tag names the
    subject (3), a title states it (2), the body merely mentions it (1).

    bm25 alone ranks a long body that repeats one common term above a short
    row whose tag is exactly the task's subject; measured on session #189's
    tasks, this second stage is what lifts #425 (tag `scoped-tests`) into the
    top eight for the task whose files name the scoped registry.
    """
    tags = _tags_text(row)
    title = str(row.get("title") or "").lower()
    body = str(row.get("content") or "").lower()
    score = 0.0
    matched: list[str] = []
    for t in terms:
        if t in tags:
            score += 3
        elif t in title:
            score += 2
        elif t in body:
            score += 1
        else:
            continue
        matched.append(t)
    return score, matched


def relevant_memory(
    be: Any,
    task: dict[str, Any],
    decisions: list[dict[str, Any]] | None = None,
    *,
    limit: int = MAX_ENTRIES,
) -> Relevance:
    """Live memory rows the task's own terms select, best bm25 first.

    Superseded rows are dropped in favour of their replacement (the same
    `superseder_of` rule the recency tail uses), and the quota is refilled
    from the ranked list so a corrected store is not punished with a shorter
    answer. Any failure inside the search returns a Relevance whose `error`
    names it; the caller prints that instead of pretending the store is empty.
    """
    terms = task_terms(task, decisions)
    if not terms:
        return Relevance([], [], None)
    try:
        rows = search_any(be, terms, n=max(limit * 8, 60))
    except Exception as e:  # noqa: BLE001 — a search failure is reported, never raised into task start
        return Relevance([], terms, f"{type(e).__name__}: {e}")
    memo: dict = {}
    live: list[tuple[float, int, dict[str, Any]]] = []
    for order, row in enumerate(rows):
        rid = as_int(row.get("id"))
        if rid is not None and superseder_of(be, "memory", rid, memo) is not None:
            continue
        row = dict(row)
        score, row["_matched"] = _score(row, terms)
        live.append((score, order, row))
    # Highest weighted match first; bm25 order (the fetch order) breaks ties.
    live.sort(key=lambda item: (-item[0], item[1]))
    return Relevance([row for _s, _o, row in live[:limit]], terms, None)


def relevance_lines(rel: Relevance, *, title_limit: int = 100) -> list[str]:
    """The block `task start` / `task show` print. Never empty when terms exist."""
    if not rel.terms:
        return []
    if rel.error:
        return [
            f"Relevant memory: search failed ({rel.error}); terms tried: {', '.join(rel.terms)}"
        ]
    if not rel.entries:
        return [f"Relevant memory: none matched {', '.join(rel.terms)}"]
    out = [f"Relevant memory ({len(rel.entries)}):"]
    for row in rel.entries:
        title = str(row.get("title") or "")
        if len(title) > title_limit:
            title = title[: title_limit - 1] + "…"
        why = ", ".join(row["_matched"][:4]) if row.get("_matched") else "bm25"
        out.append(f"- #{row.get('id')} [{row.get('type')}] {title} ← {why}")
    return out


def lines_for_task(be: Any, slug: str, task: dict[str, Any] | None = None) -> list[str]:
    """What `task start` / `task show` print for `slug`: named when empty,
    degraded to a named line on any failure, never raised into the caller."""
    try:
        row = task if task is not None else be.task_get_full(slug)
        if not row:
            return []
        decisions = row.get("decisions")
        if decisions is None:
            decisions = be.decisions_for_task(slug)
        return relevance_lines(relevant_memory(be, row, decisions))
    except Exception as e:  # noqa: BLE001 — recall is advisory; task start must not fail on it
        return [f"Relevant memory: search failed ({type(e).__name__}: {e})"]


__all__ = [
    "MAX_ENTRIES",
    "Relevance",
    "lines_for_task",
    "relevance_lines",
    "relevant_memory",
    "search_any",
    "task_terms",
]
