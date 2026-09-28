"""The documentation map is held by a test, in BOTH directions.

MEASURED BEFORE the map existed: 64 EN pages and 63 RU pages, of which 17 and 23 were
reachable from no navigation section at all, and not one page said who it was for. A reader
of the framework, an agent executing it and someone changing the core were handed the same
undifferentiated list.

WHY THE TEST MATTERS MORE THAN THE MAP. A map is a document, and a document with no owner
goes stale the way this project has already measured twice: a root file claiming to be the
map of the project's direction sat two releases behind, and a hand-written registry excused
a missing English contract with a reason that was false. So the map is generated from
declarations inside the pages, and this file asserts the two directions that can rot:

  * a page outside the map — a page with no declaration, or with a zone/reader the closed
    lists do not contain;
  * a record without a page — the generated file disagreeing with the tree, which is what
    `--check` compares.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

#: The map reads both language trees, so a change to either must select this file.
CROSSCUTTING_SCOPE = ["docs/en/", "docs/ru/"]


def _collect():
    from doc_map import collect

    return collect(_REPO)


#: The two ways a page can be missing from the map, and what each one means. A table rather
#: than a test apiece: both read one key of `findings` and assert it is empty, which is the
#: same shape twice — the dedupe ratchet counts that, and it is right to.
_FORWARD_FINDINGS = (
    (
        "undeclared",
        "pages with no `<!-- doc-map: reader=…; zone=… -->` declaration, or with a reader or "
        "zone outside the closed lists. Guessing one would produce a map that looks complete "
        "and answers the wrong question, which is worse than an empty cell because nobody "
        "re-checks a filled one",
    ),
    (
        "conflicting",
        "pages whose language halves declare a DIFFERENT reader or zone — a pair is one page "
        "in two languages, and two readers would mean two documents",
    ),
)


@pytest.mark.parametrize("kind,meaning", _FORWARD_FINDINGS)
def test_no_page_is_missing_from_the_map(kind, meaning):
    """AC2 forward: a page outside the map is a finding, not a default."""
    from doc_map import findings

    found = findings(_collect())
    assert not found[kind], f"{meaning}: " + ", ".join(found[kind])


def test_the_generated_map_is_fresh():
    """AC2 backward: a record without a page, or a page without a record.

    `--check` compares the rendered map with the committed file, so a page added or moved
    without reissuing the map reddens here rather than being discovered by a reader.
    """
    rc = subprocess.run(  # ruff-not-enabled: S603 - fixed argv, shell=False
        [sys.executable, "scripts/doc_map.py", "--check", "--repo-root", str(_REPO)],
        cwd=_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    assert rc.returncode == 0, (
        "the generated map is stale or has findings — reissue with "
        "`python scripts/doc_map.py --write`:\n" + (rc.stdout or "")[-2000:]
    )


def test_the_map_covers_every_page_on_disk():
    """The premise. A collector that silently skipped files would keep every test above
    green while the map described a smaller tree than the one that exists."""
    records = _collect()
    on_disk = {
        name
        for lang in ("en", "ru")
        for name in os.listdir(_REPO / "docs" / lang)
        if name.endswith(".md")
    }
    assert set(records) == on_disk, f"map {len(records)} vs tree {len(on_disk)}"
    assert len(on_disk) > 50, f"only {len(on_disk)} pages found — the collector broke"


@pytest.mark.parametrize("reader", ["user", "agent", "maintainer"])
def test_each_reader_actually_has_pages(reader):
    """An axis on which every page lands in one bucket is not an axis.

    The point of declaring a reader is that a page written for everybody is written for
    nobody; if one of the three were empty, the declaration would be decoration.
    """
    records = _collect()
    mine = [n for n, r in records.items() if r["reader"] == reader]
    assert mine, f"no page is declared for `{reader}` — the axis collapsed"


def test_a_page_with_an_unknown_zone_is_not_silently_accepted(tmp_path):
    """NEGATIVE: the closed lists have to refuse, or they are documentation of intent."""
    from doc_map import marker

    assert marker("<!-- doc-map: reader=user; zone=core-surface -->") == ("user", "core-surface")
    assert marker("<!-- doc-map: reader=user; zone=whatever -->") is None
    assert marker("<!-- doc-map: reader=everyone; zone=core-surface -->") is None
    assert marker("no marker here") is None
