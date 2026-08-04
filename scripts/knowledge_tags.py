"""One spelling of a tag list, so a mixed result set can be rendered by one reader.

THE CANONICAL FORM IS A JSON ARRAY, and it is the project store's form rather
than a new one. The shared store used to write `",".join(tags)` while the
project store wrote and read `json.dumps`/`json.loads`, and nothing broke,
because neither the CLI search nor the MCP formatter printed tags at all. A
divergence nobody can observe is still a divergence: it detonates on the next
obvious improvement, which is a single tag renderer over a result set holding
both kinds of row. That renderer either swallows the `JSONDecodeError` — the
project code already catches it — and shows "no tags" for shared rows that have
them, or it raises. Both are worse than migrating a handful of rows now.

WHY CONVERGE INSTEAD OF PINNING THE DIVERGENCE WITH A TEST. The alternative on
the table was to declare two formats legal and require every future reader to
handle both. That is a tax on code that has not been written yet, levied to
avoid one migration today while the shared store holds a few dozen rows. The
cost of the migration only grows.

WHAT CANNOT BE RECOVERED, stated rather than guessed at. A tag containing a
comma was already destroyed by the CSV write — `["a,b"]` and `["a", "b"]` both
became `a,b`, and nothing in the stored value distinguishes them. The migration
reads it as two tags, which is the commoner case, and does not pretend to know.
"""

from __future__ import annotations

import json


def dump_tags(tags: list[str] | None) -> str | None:
    """The canonical stored form. None stays None — an absent list is not `[]`."""
    if not tags:
        return None
    return json.dumps(tags, ensure_ascii=False)


def load_tags(raw: str | None) -> list[str]:
    """Read either form. Total: no input makes this raise.

    Accepting the legacy spelling here as well as migrating it is deliberate
    belt-and-braces — a store opened read-only, or by a process that never
    reaches the migration, still renders correctly rather than showing nothing.
    """
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return _from_csv(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return _from_csv(text)
    return _from_csv(text)


def _from_csv(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def normalized_tags(raw: str | None) -> str | None:
    """The canonical form of a stored value, or None when it must not be touched.

    None rather than the input, for the same reason the origin redaction does
    it: "nothing to do" and "rewrite to an identical value" have to stay
    distinguishable, so a migration's count remains an honest measure of what
    was actually in the legacy shape.

    Empty and NULL are left alone — they are not a divergence, and turning them
    into `[]` would replace an absent list with an empty one, which the read
    side would then have to tell apart for no gain.
    """
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            pass
        else:
            # A list of STRINGS is canonical. A list holding anything else —
            # `[1, 2]`, `[null, "tag"]`, `[["a"], "b"]` — is not, and this
            # migration is the one chance to say so. Left alone it would be read
            # forever through `str(item)`, rendering as `None` or `['a']` on
            # every screen while never being flagged as needing repair.
            if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                return None  # already canonical
    tags = load_tags(raw)
    if not tags:
        return None
    return dump_tags(tags)
