"""Where the release notes live, per language — stated and checked.

Since 1.9 the GitHub tag is lightweight (see docs/en/publishing.md), so the
notes a reader meets on GitHub are the body of the GitHub Release. That body is
written in English. The full text lives in two pages, docs/en/whats-new-X.Y.md
and docs/ru/whats-new-X.Y.md, and the body MUST link both — the Russian reader
otherwise lands on a page that does not speak to them.

This was a choice found after the fact when 1.8 was reconciled; now it is a
rule with a check. `tausik publish notes --version X.Y.Z --body-file F` runs it
before the owner creates the release; it refuses a body that misses a page.
"""

from __future__ import annotations

import re

LANGS = ("en", "ru")


def whats_new_page(version: str, lang: str) -> str:
    """The page a release links for `lang`: docs/<lang>/whats-new-<major.minor>.md."""
    m = re.match(r"v?(\d+)\.(\d+)", version.strip())
    if not m:
        raise ValueError(f"not a release version: {version!r}")
    return f"docs/{lang}/whats-new-{m.group(1)}.{m.group(2)}.md"


def missing_links(body: str, version: str) -> list[str]:
    """Pages of `version` the release body does not link; empty when both are there."""
    return [page for page in (whats_new_page(version, lang) for lang in LANGS) if page not in body]
