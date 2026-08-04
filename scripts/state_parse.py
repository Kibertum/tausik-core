"""Parsing primitives for the git-native state import — the inverse of the emitter.

`state-git-import` reconstructs the DB cache from the `tausik/` tree. Correctness
rests on this module being the exact inverse of :mod:`state_serialize`'s emitter:
parse(emit(x)) == x for every durable value. It is deliberately stdlib-only and
tailored to the emitter's RESTRICTED YAML subset (flat scalars, block lists of
scalars, block lists of `relation/target_type/target` edge mappings) — not a
general YAML parser, so the round-trip is closed and dependency-free, matching the
emitter's own stdlib choice.

Body prose is recovered by the FIXED ordered heading grammar the contract mandates
(team-state-in-git.md, negative scenario 4): sections are sliced by the known
titles in order, so a `## Journal` embedded in Plan prose cannot forge the real
Journal (which is the last section).
"""

from __future__ import annotations

import re

_INT_RE = re.compile(r"^-?\d+$")


class ParseError(Exception):
    """A malformed file the import refuses to guess at (bad frontmatter, no slug)."""


def unescape_dq(s: str) -> str:
    """Reverse state_serialize._dq: decode a double-quoted scalar's body."""
    out: list[str] = []
    i = 0
    table = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append(table.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def parse_scalar(token: str) -> str | int | None:
    """Inverse of state_serialize.scalar: `null`→None, `"..."`→str, digits→int."""
    if token == "null":
        return None
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return unescape_dq(token[1:-1])
    if _INT_RE.match(token):
        # Only call_budget is emitted as a bare int; every number-like STRING is
        # quoted by the emitter, so a bare all-digits token is a genuine integer.
        return int(token)
    return token


def split_file(content: str) -> tuple[str, str]:
    """Split an entity file into (frontmatter_text, body). Raises on a missing fence.

    Partition on the FIRST `---\\n` after the opening fence: the emitter never puts
    a bare `---` line inside frontmatter (such a value would be quoted), so the
    first closing fence is always the real one even if the body contains `---`.
    """
    if not content.startswith("---\n"):
        raise ParseError("missing opening '---' frontmatter fence")
    fm_text, sep, after = content[4:].partition("---\n")
    if not sep:
        raise ParseError("missing closing '---' frontmatter fence")
    return fm_text, after.strip("\n")


def _parse_block_list(lines: list[str], i: int) -> tuple[list, int]:
    """Parse a block list starting at line `i`; return (items, next_index).

    Items are either scalars (`  - value`) or edge mappings whose first line is
    `  - relation: ...` followed by indented `    target_type:` / `    target:`.
    """
    items: list = []
    while i < len(lines) and lines[i].startswith("  - "):
        body = lines[i][4:]
        if body.startswith("relation:"):
            item: dict[str, object] = {}
            k, _, v = body.partition(":")
            item[k.strip()] = parse_scalar(v.strip())
            i += 1
            while (
                i < len(lines)
                and lines[i].startswith("    ")
                and not lines[i].lstrip().startswith("- ")
            ):
                k, _, v = lines[i].strip().partition(":")
                item[k.strip()] = parse_scalar(v.strip())
                i += 1
            items.append(item)
        else:
            items.append(parse_scalar(body.strip()))
            i += 1
    return items, i


def parse_frontmatter(fm_text: str) -> dict:
    """Parse the emitter's restricted YAML frontmatter into a dict.

    Scalars via :func:`parse_scalar`; `key: []` → empty list; `key:` followed by
    indented `  - ` lines → a block list. Key order is irrelevant to the result.
    """
    lines = fm_text.split("\n")
    result: dict[str, object] = {}
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip() or line.startswith(" "):
            i += 1
            continue
        key, sep, rest = line.partition(":")
        if not sep:
            raise ParseError(f"malformed frontmatter line: {line!r}")
        key = key.strip()
        val = rest.strip()
        if val == "":
            items, i = _parse_block_list(lines, i + 1)
            result[key] = items
        elif val == "[]":
            result[key] = []
            i += 1
        else:
            result[key] = parse_scalar(val)
            i += 1
    return result


def parse_sections(body: str, titles: list[str]) -> dict[str, str]:
    """Slice body prose into {title: content} by the FIXED ordered heading set.

    Each `## <title>` is located strictly AFTER the previous title's heading, so a
    known heading embedded in an earlier section's prose does not steal it — the
    contract's defense against a forged `## Journal` inside Plan text. A title with
    no heading maps to "".
    """
    result: dict[str, str] = {t: "" for t in titles}
    lines = body.split("\n")
    # index the line of each title heading, scanning forward in order
    positions: dict[str, int] = {}
    search_from = 0
    for t in titles:
        marker = f"## {t}"
        for idx in range(search_from, len(lines)):
            if lines[idx].rstrip() == marker:
                positions[t] = idx
                search_from = idx + 1
                break
    ordered = [t for t in titles if t in positions]
    for pos, t in enumerate(ordered):
        start = positions[t] + 1
        end = positions[ordered[pos + 1]] if pos + 1 < len(ordered) else len(lines)
        result[t] = "\n".join(lines[start:end]).strip()
    return result


_JOURNAL_RE = re.compile(r"^- (?P<ts>\S+)(?: \[(?P<phase>[^\]]+)\])? — (?P<msg>.*)$")


def parse_journal(section: str) -> list[dict[str, str | None]]:
    """Parse a `## Journal` section body into [{created_at, phase, message}]."""
    rows: list[dict[str, str | None]] = []
    for line in section.split("\n"):
        m = _JOURNAL_RE.match(line.strip())
        if m:
            rows.append({"created_at": m["ts"], "phase": m["phase"], "message": m["msg"]})
    return rows
