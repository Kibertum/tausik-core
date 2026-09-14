"""Render the answer: definition inlined, so no file has to be opened after it.

This is the part of Graft worth copying. Its measured saving does not come from
having a graph — it comes from `graft ask` returning the SOURCE inside the
answer, so the agent stops at one call instead of grep → read → maybe read again.

Measured here before building anything (session #233, eight transcripts):
`grep/sed/find/ls` through Bash is 1,192 calls and 37.1% of all tool result
payload, at 1,501 characters a call; the dedicated navigation tools add 9.6%.
Roughly 47% of everything tools returned was code exploration. That is the share
this answer competes with.

THE ANSWER IS BOUNDED AND SAYS SO. A definition of a thousand lines poured into
the context is exactly the expensive file read this replaces, so the body is cut
at a stated number of lines and the cut is NAMED. An answer that silently
truncates teaches the reader to open the file anyway, which costs both.
"""

from __future__ import annotations

from pathlib import Path

from symbol_index import DEFAULT_BODY_LINES, Symbol, build_index, callers_of, roots_for

#: How many callers to list before saying how many more there are. A caller list
#: is a hint about where to look next, not a report; past a dozen it stops
#: helping and starts costing.
MAX_CALLERS = 12

#: How many matching definitions to render in full before saying how many more
#: there are. Rendering everything named `run` would out-cost the grep it
#: replaces.
MAX_MATCHES = 5


def find(symbols: list[Symbol], query: str) -> list[Symbol]:
    """Symbols matching `query` — exact name, `Class.method`, or a substring.

    Exact matches come first and alone when they exist: a query that names a
    real symbol should not be diluted by everything that merely contains it.
    """
    exact = [s for s in symbols if s.name == query or s.qualname == query]
    if exact:
        return exact
    lowered = query.lower()
    return [s for s in symbols if lowered in s.qualname.lower()]


def _body(repo_root: Path, sym: Symbol, max_lines: int) -> tuple[str, int]:
    """(text, lines_omitted) for the definition, cut at `max_lines`."""
    try:
        lines = (repo_root / sym.path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return "", 0
    chunk = lines[sym.lineno - 1 : sym.end_lineno]
    if len(chunk) <= max_lines:
        return "\n".join(chunk), 0
    return "\n".join(chunk[:max_lines]), len(chunk) - max_lines


def answer(
    repo_root: str | Path,
    query: str,
    *,
    max_lines: int = DEFAULT_BODY_LINES,
    roots: tuple[str, ...] | None = None,
    with_callers: bool = True,
) -> str:
    """One answer, complete enough that opening the file is unnecessary."""
    root = Path(repo_root)
    source = "caller"
    if roots is None:
        roots, source = roots_for(root)
    symbols = build_index(root, roots)
    matches = find(symbols, query)

    if not matches:
        return _nothing_found(symbols, query, roots, source)

    parts: list[str] = []
    for sym in matches[:MAX_MATCHES]:
        text, omitted = _body(root, sym, max_lines)
        parts.append(f"{sym.path}:{sym.lineno}  ({sym.kind})")
        parts.append("```python")
        parts.append(text)
        if omitted:
            # NAMED, not silent: the reader has to know whether this is the whole
            # definition or the start of one.
            parts.append(f"# ... {omitted} more line(s) — full text at {sym.path}:{sym.lineno}")
        parts.append("```")
        if with_callers:
            parts.append(_callers_line(root, sym, roots))
        parts.append("")

    if len(matches) > MAX_MATCHES:
        parts.append(
            f"{len(matches) - MAX_MATCHES} further match(es) not shown — narrow the query."
        )
    parts.append(_roots_line(roots, source))
    return "\n".join(parts).rstrip() + "\n"


def _roots_line(roots: tuple[str, ...], source: str) -> str:
    """Where the answer looked, and on whose authority.

    On the POSITIVE answer as well as the negative one. A reader who cannot see
    the search area cannot tell a complete answer from one that happened to miss
    a whole subtree — and until this release the area was a constant naming THIS
    repository's directories, so in somebody else's project that difference was
    the entire result.
    """
    where = {
        "declared": "declared in .tausik/config.json",
        "git": "derived from git-tracked files",
        "disk": "scanned from disk — not a git repository",
        "fallback": (
            "NOT DERIVED — no source was located in this tree, so the framework's own "
            "layout was assumed and this answer may be about the wrong files"
        ),
        "caller": "given by the caller",
    }.get(source, source)
    return f"searched: {', '.join(roots)} ({where})"


def _callers_line(root: Path, sym: Symbol, roots: tuple[str, ...]) -> str:
    hits = [h for h in callers_of(root, sym.name, roots) if h != f"{sym.path}:{sym.lineno}"]
    if not hits:
        return "called from: nothing in the indexed tree"
    shown = ", ".join(hits[:MAX_CALLERS])
    more = f" (+{len(hits) - MAX_CALLERS} more)" if len(hits) > MAX_CALLERS else ""
    return f"called from: {shown}{more}"


def _nothing_found(
    symbols: list[Symbol], query: str, roots: tuple[str, ...], source: str = "caller"
) -> str:
    """Absence, with the nearest thing to it — never an empty answer.

    An empty result is indistinguishable from a broken index, and a reader who
    cannot tell those apart goes back to grepping, which is the cost this exists
    to remove.
    """
    lowered = query.lower()
    stem = lowered[:4]
    near = sorted({s.qualname for s in symbols if stem and stem in s.qualname.lower()})[:8]
    lines = [
        f"no symbol named {query!r} in the indexed tree ({len(symbols)} definitions).",
        # WHERE the search area came from, not only what it was. "Nothing here"
        # and "we were looking in the framework's own directory names because we
        # could not find yours" are different answers, and only one of them is
        # about the symbol. The root list lives HERE and not in the line above:
        # printing it twice made the answer longer without making it truer.
        _roots_line(roots, source),
    ]
    if near:
        lines.append("nearest names: " + ", ".join(near))
    else:
        lines.append(
            "nothing similar either — a symbol defined outside "
            f"{', '.join(roots)} is out of the index by design, not missing."
        )
    return "\n".join(lines) + "\n"
