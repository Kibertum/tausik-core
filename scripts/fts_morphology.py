"""Word forms for FTS5 search on a Russian corpus, inside FTS5 (github#124).

search-has-no-morphology-and-strips-the-wildcard (1.10). The FTS tables use the
unicode61 tokenizer — no stemming — and the sanitizer stripped `*`, so prefix
search, FTS5's own way to reach word forms, was unreachable. Measured before:
«гейт» found 486 records and «гейтами» 13; each form found only itself.

Chosen, of three: (a) a trailing `*` is kept, so an agent can type `гейт*`; and
a Cyrillic token of five letters or more is expanded to `(form OR stem*)`, the
stem being the form without a common ending (at least four letters kept). Not
(b) "prefix only when few hits": «гейтами» had 13 hits and would never expand.
Not (c) a trigram tokenizer: it rebuilds every index and was not needed. Vectors
stay closed (l26-embeddings-revisit).
"""

from __future__ import annotations

import re

_CYR_WORD = re.compile(r"^[А-Яа-яЁё]{5,}$")
# Longest first, so «ями» is tried before «и».
_ENDINGS = tuple(
    sorted(
        (
            "ами",
            "ями",
            "ого",
            "его",
            "ому",
            "ему",
            "ыми",
            "ими",
            "иях",
            "ией",
            "ой",
            "ей",
            "ам",
            "ям",
            "ах",
            "ях",
            "ов",
            "ев",
            "ом",
            "ем",
            "ую",
            "юю",
            "ая",
            "яя",
            "ые",
            "ие",
            "ый",
            "ий",
            "ы",
            "и",
            "а",
            "я",
            "у",
            "ю",
            "е",
            "о",
            "ь",
        ),
        key=len,
        reverse=True,
    )
)
MIN_STEM = 4


def stem(word: str) -> str:
    low = word.lower()
    for end in _ENDINGS:
        if low.endswith(end) and len(low) - len(end) >= MIN_STEM:
            return low[: -len(end)]
    return low


def expand(token: str) -> str:
    """`(token OR stem*)` for a long Cyrillic token; the token unchanged otherwise."""
    if not _CYR_WORD.match(token):
        return token
    base = stem(token)
    return f"({token} OR {base}*)" if base != token.lower() else f"{base}*"


_TRAILING_STAR = re.compile(r"^([\w]{3,})\*$", re.UNICODE)


def keep_trailing_star(token: str) -> str | None:
    """`гейт*` stays a prefix query; any other star placement returns None."""
    m = _TRAILING_STAR.match(token)
    return f"{m.group(1)}*" if m else None
