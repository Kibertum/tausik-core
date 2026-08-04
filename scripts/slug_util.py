"""Stable, machine-independent slugs for decisions and memory (state-git-stable-ids).

Tasks are already addressed by slugs, so two engineers on two branches never
collide on a task id. Decisions and memory used local autoincrement ids (#171,
#307) — both branches mint "#308" and a `git merge` of the exported state
duplicates or clobbers. This turns the human-meaningful title (or a decision's
first line) into a slug that is the SAME on every machine for the same content,
so the git-native projection merges by identity, not by a local counter.

Charset decision (the spec, `team-state-in-git.md`, defers slug stabilisation
to THIS task): slugs are ASCII kebab-case. The live data is Russian, and a bare
ASCII-fold would empty every Cyrillic title into an id fallback — unreadable and
useless as a filename. So Cyrillic is TRANSLITERATED to Latin first (доменная →
domennaya), giving a portable, git-friendly, human-readable `tausik/memory/<slug>.md`
that behaves the same on NTFS, ext4 and APFS. Determinism is the whole point: the
same text yields the same slug byte-for-byte, on any machine, forever — so the
transliteration table and the dedup order are frozen, never "improved" casually.
"""

from __future__ import annotations

import re
import sqlite3

# Frozen practical Russian→Latin transliteration. NOT a place to tinker: every
# edit re-slugs history and breaks the byte-identical round-trip the whole epic
# rests on. Lowercase only — callers lowercase before mapping.
_CYRILLIC_TO_LATIN: dict[str, str] = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

# Longest slug we keep. A file name, not a sentence — long enough to stay
# readable, short enough for legacy path limits. Trim happens on a `-` boundary
# so a word is never cut mid-transliteration.
_MAX_SLUG_LEN = 60

_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")


def transliterate(text: str) -> str:
    """Map Cyrillic to Latin; leave everything else untouched (slugify strips it)."""
    return "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in text.lower())


def slugify(text: str) -> str:
    """kebab-case ASCII slug, or ``""`` when `text` carries nothing usable.

    Transliterate → collapse every run of non-`[a-z0-9]` to a single `-` → trim
    to `_MAX_SLUG_LEN` on a hyphen boundary → strip leading/trailing `-`.
    """
    ascii_text = transliterate(text)
    slug = _NON_SLUG_RE.sub("-", ascii_text).strip("-")
    if len(slug) <= _MAX_SLUG_LEN:
        return slug
    cut = slug[:_MAX_SLUG_LEN]
    # Prefer the last whole segment; fall back to the hard cut if the first
    # segment alone already exceeds the cap.
    if "-" in cut:
        cut = cut.rsplit("-", 1)[0]
    return cut.strip("-")


def dedup(base: str, taken: set[str] | frozenset[str]) -> str:
    """Return `base`, or `base-2`/`base-3`/… — the first not already in `taken`.

    Deterministic by construction: called in a fixed order (id ASC during
    backfill), the same collisions resolve to the same suffixes on every machine.
    """
    if base not in taken:
        return base
    i = 2
    while f"{base}-{i}" in taken:
        i += 1
    return f"{base}-{i}"


def make_slug(text: str, *, fallback: str, taken: set[str] | frozenset[str]) -> str:
    """A unique, deterministic slug for `text`, unique against `taken`.

    `text` is the human source (a memory title, a decision's first line).
    `fallback` is a caller-supplied seed used ONLY when `text` slugifies to
    nothing (empty title, punctuation-only decision) — e.g. ``decision-171`` or
    ``memory-2026-07-24t20-42-04z`` — so the result is never NULL and never
    crashes the migration. The caller must NOT pass this into the `taken` set for
    the same row; `dedup` handles collisions among fallbacks too.
    """
    base = slugify(text) or slugify(fallback) or "item"
    return dedup(base, taken)


def first_line(text: str) -> str:
    """The first non-empty line of `text` — a decision's de-facto title."""
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


# The only tables that carry a slug. `next_slug` interpolates `table` into SQL,
# so it is an allowlist, not a hint: a caller passing anything else is a bug (or
# an injection attempt) and fails loudly instead of building arbitrary SQL.
_SLUG_TABLES = frozenset({"decisions", "memory"})


def next_slug(query, table: str, text: str, fallback: str) -> str:
    """A stable slug for a NEW row in `table`, unique against its existing slugs.

    `query` is a callable returning row-dicts (a backend's ``_q``). Uses the same
    generator as the v42 backfill, so a row created now and one migrated from
    history obey one identity rule (state-git-stable-ids). This is a best-effort
    PRE-dedup: the UNIQUE index is the real guarantee, enforced via
    ``insert_with_slug`` (a concurrent writer can still take our slug first).
    """
    if table not in _SLUG_TABLES:
        raise ValueError(f"next_slug: unknown table {table!r} (allowed: {sorted(_SLUG_TABLES)})")
    taken = {
        r["slug"]
        for r in query(f"SELECT slug FROM {table} WHERE slug IS NOT NULL AND slug != ''")
        if r.get("slug")
    }
    return make_slug(text, fallback=fallback, taken=taken)


def insert_with_slug(query, insert, table: str, text: str, fallback: str, *, retries: int = 5):
    """Allocate a unique slug and run ``insert(slug)``, retrying on a UNIQUE clash.

    ``next_slug`` reads the taken set and the caller INSERTs in a separate
    statement, so two concurrent writers (the backend connection is
    ``check_same_thread=False``) can compute the same base slug and both try to
    insert it. The UNIQUE index turns the loser's INSERT into an IntegrityError;
    here we re-query and retry with the next suffix, so the collision is
    corrected — never a crash, never a silent duplicate. Retries are bounded; the
    last IntegrityError is re-raised if they run out (loud, not swallowed).
    """
    last: sqlite3.IntegrityError | None = None
    for _ in range(max(1, retries)):
        slug = next_slug(query, table, text, fallback)
        try:
            return insert(slug)
        except sqlite3.IntegrityError as exc:
            last = exc
    raise last if last is not None else RuntimeError("insert_with_slug: no attempt made")
