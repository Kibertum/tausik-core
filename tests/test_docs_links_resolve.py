"""Every relative link in the documentation resolves — on GitHub, in a clone, anywhere.

Measured in session #251 over 224 tracked Markdown files: 592 relative links,
116 unresolvable — 73 of them the language switcher on every page of
`docs/en` and `docs/ru`, written as a site route (`/ru/docs/quickstart`,
`/docs/hooks`) for the VitePress site that has since moved to its own
repository (tausik/site). On GitHub and in a checkout those were dead links,
one per page, and nothing said so: the full-tree link check was deferred in
`d7-cross-link-check` (April) and never arrived. This is that check.

What is NOT checked, and why:
* `CHANGELOG*.md` — a historical record; an entry links to files as they were
  (the brain modules removed with Notion), and rewriting history to keep links
  green would be the wrong fix.
* `docs/**/research/` — dated notes; internal links inside them are fixed
  where found but the sink is not held to the standard of the live pages.
* `TODO.md` — not documentation and not part of the public snapshot (#368).
"""

from __future__ import annotations

from pathlib import Path

import os
import re

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CROSSCUTTING_SCOPE = ["docs/", "README.md", "README.ru.md", "AGENTS.md"]

_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
_SITE_ROUTE = re.compile(r"^/(?:ru/docs|docs/ru|docs)/")
_ROOT_PAGES = ("README.md", "README.ru.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md")


#: Pages that have no pair in the other language ON PURPOSE, read from the page
#: ITSELF — the `<!-- audit-translation-drift: unpaired: <reason> -->` marker.
#:
#: THIS USED TO BE A HAND-WRITTEN DICT, and the second copy did what second copies
#: do. Its entry for the extended contract read "the EN reader is served by
#: AGENTS.md", which was not true: AGENTS.md is an onboarding page and CLAUDE.md
#: calls the contract FULL, so an English-branch reader had no contract at all.
#: A registry away from its subject carried an excuse for years; the marker sits
#: in the file a translator opens, and one source cannot disagree with itself.
def singletons() -> dict[str, str]:
    import sys

    scripts = os.path.join(_ROOT, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from audit_translation_drift import unpaired_reason

    out: dict[str, str] = {}
    for lang in ("en", "ru"):
        folder = os.path.join(_ROOT, "docs", lang)
        for name in os.listdir(folder):
            if not name.endswith(".md"):
                continue
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                reason = unpaired_reason(fh.read())
            if reason:
                out[f"docs/{lang}/{name}"] = reason
    return out


def _pages() -> list[str]:
    out = [p for p in _ROOT_PAGES if os.path.isfile(os.path.join(_ROOT, p))]
    for lang in ("en", "ru"):
        d = os.path.join(_ROOT, "docs", lang)
        out += sorted(os.path.join("docs", lang, f) for f in os.listdir(d) if f.endswith(".md"))
    if os.path.isfile(os.path.join(_ROOT, "docs", "README.md")):
        out.append("docs/README.md")
    return out


def _broken(rel_page: str, text: str) -> list[str]:
    bad: list[str] = []
    base = os.path.dirname(os.path.join(_ROOT, rel_page))
    for m in _LINK.finditer(text):
        target = m.group(1)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if _SITE_ROUTE.match(target):
            bad.append(f"{target} (site route — the site lives in tausik/site)")
            continue
        path = target.split("#", 1)[0]
        if not path or "<" in path:
            continue  # an anchor-only link, or a documented placeholder
        if not os.path.exists(os.path.normpath(os.path.join(base, path))):
            bad.append(target)
    return bad


@pytest.mark.parametrize("page", _pages())
def test_every_relative_link_resolves(page):
    text = Path(os.path.join(_ROOT, page)).read_text(encoding="utf-8")
    broken = _broken(page, text)
    assert not broken, f"{page}: {broken}"


def _pairs() -> list[tuple[str, str]]:
    en = {f for f in os.listdir(os.path.join(_ROOT, "docs", "en")) if f.endswith(".md")}
    ru = {f for f in os.listdir(os.path.join(_ROOT, "docs", "ru")) if f.endswith(".md")}
    return sorted((f, f) for f in en & ru)


def test_every_page_has_its_pair_or_is_a_declared_singleton():
    en = {f for f in os.listdir(os.path.join(_ROOT, "docs", "en")) if f.endswith(".md")}
    ru = {f for f in os.listdir(os.path.join(_ROOT, "docs", "ru")) if f.endswith(".md")}
    lonely = {f"docs/en/{f}" for f in en - ru} | {f"docs/ru/{f}" for f in ru - en}
    declared = singletons()
    undeclared = lonely - set(declared)
    stale = set(declared) - lonely
    assert not undeclared, f"pages without a pair in the other language: {sorted(undeclared)}"
    assert not stale, f"declared singletons that now have a pair — drop them: {sorted(stale)}"


@pytest.mark.parametrize("en_name,ru_name", _pairs())
def test_the_switcher_points_at_the_pair(en_name, ru_name):
    en_text = Path(os.path.join(_ROOT, "docs", "en", en_name)).read_text(encoding="utf-8")
    ru_text = Path(os.path.join(_ROOT, "docs", "ru", ru_name)).read_text(encoding="utf-8")
    assert f"../ru/{ru_name}" in en_text, f"docs/en/{en_name} has no switcher to its RU pair"
    assert f"../en/{en_name}" in ru_text, f"docs/ru/{ru_name} has no switcher to its EN pair"


def test_a_dead_link_and_a_site_route_are_caught():
    """Negative: the checker sees both kinds it exists for."""
    bad = _broken("docs/en/hooks.md", "see [x](nothing-here.md) and [y](/ru/docs/hooks)")
    assert any("nothing-here.md" in b for b in bad)
    assert any("site route" in b for b in bad)
    assert _broken("docs/en/hooks.md", "see [ok](hooks.md#anchor) and [web](https://x.y)") == []
