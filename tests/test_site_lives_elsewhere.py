"""tausik.tech lives in its own GitLab repository (tausik/site); core carries no trace.

Decision #368 (session #251): the site was extracted (stories
extract-site-gitlab, core-github-cleanup) and the owner asked that this be
MEASURED and held, not remembered. Measured in session #255 over the tracked
tree of core HEAD and over `github/main`: zero files matching the declared
signs of a site build. This test keeps core at zero; the public line is
checked when the remote is reachable and named as unmeasured otherwise —
a check that passes without dialling says nothing about the mirror.

A LINK to tausik.tech in README or docs is not a trace of the site; it is a
pointer to it, and it is not forbidden here.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CROSSCUTTING_SCOPE = ["docs/", "README.md", "README.ru.md"]

#: Declared signs of a site build, matched against tracked paths. Anchored on
#: a path segment so `docs/site-notes.md` (prose about the site) is not one.
SITE_SIGNS: tuple[tuple[str, str], ...] = (
    ("a `site/` directory", r"(^|/)site/"),
    ("a VitePress config directory", r"(^|/)\.vitepress/"),
    ("a Vue single-file component", r"\.vue$"),
    (
        "a Node package manifest or lockfile",
        r"(^|/)(package(-lock)?\.json|pnpm-lock\.yaml|yarn\.lock)$",
    ),
    ("a Vite config", r"(^|/)vite\.config\.[cm]?[jt]s$"),
    ("an nginx site config", r"(^|/)nginx[^/]*\.conf$"),
    ("a site Dockerfile / compose file", r"(^|/)(Dockerfile|docker-compose\.ya?ml)$"),
)


def _matches(paths: list[str]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for label, pattern in SITE_SIGNS:
        rx = re.compile(pattern)
        hits.extend((label, p) for p in paths if rx.search(p))
    return hits


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def test_core_carries_no_site_build():
    r = _git(["ls-files"])
    assert r.returncode == 0, r.stderr
    hits = _matches(r.stdout.split())
    assert not hits, f"site build files came back into core: {hits}"


def test_the_public_line_carries_no_site_build_or_says_it_was_not_measured():
    """`github/main` via the ref this checkout holds — no network dial here
    (the fetch is the owner's act); a checkout without the ref cannot measure
    the mirror and says so instead of passing."""
    r = _git(["ls-tree", "-r", "--name-only", "github/main"])
    if r.returncode != 0:
        pytest.skip(
            "github/main is not a known ref in this checkout — the mirror is unmeasured here"
        )
    hits = _matches(r.stdout.split())
    assert not hits, f"site build files on the public line: {hits}"


def test_a_returning_site_file_is_caught():
    """Negative: one `site/index.html` or one `package.json` reddens."""
    assert _matches(["site/index.html"]) and _matches(["package.json"])
    assert _matches(["docs/en/site-notes.md"]) == []
    assert _matches(["README.md"]) == []
