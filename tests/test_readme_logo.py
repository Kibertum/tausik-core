"""Every image the front pages show is a file in the repository.

The mark went in on 2026-09-13 (two renderings under docs/assets/, the choice of
which goes where written beside them). An `<img>` in Markdown is not a link the
docs-links test resolves, so a moved or renamed asset would leave a broken
picture at the top of README with nothing going red — this does.
"""

from __future__ import annotations

from pathlib import Path

import os
import re

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PAGES = ["README.md", "README.ru.md", "docs/README.md"]
CROSSCUTTING_SCOPE = ["README.md", "README.ru.md", "docs/README.md", "docs/assets/"]
_IMG = re.compile(r"<img\s[^>]*src=\"([^\"]+)\"")


def _images(rel: str) -> list[str]:
    text = Path(os.path.join(_ROOT, rel)).read_text(encoding="utf-8")
    return _IMG.findall(text)


@pytest.mark.parametrize("page", _PAGES)
def test_every_image_on_the_page_is_a_file(page):
    refs = _images(page)
    assert refs, f"{page} shows no image — the mark is gone"
    base = os.path.dirname(os.path.join(_ROOT, page))
    for src in refs:
        assert not src.startswith(("http://", "https://", "/")), (
            f"{page}: {src} must be repository-relative"
        )
        assert os.path.isfile(os.path.join(base, src)), f"{page}: {src} is not a file"


def test_every_page_carries_the_one_logo_and_the_colour_rendering_is_placed_nowhere():
    """Owner, 2026-09-14: the monoline is the logo; the colour rendering is
    kept as `-full` and sits on no page."""
    assert _images("README.md") == ["docs/assets/tausik-logo.png"]
    assert _images("README.ru.md") == ["docs/assets/tausik-logo.png"]
    assert _images("docs/README.md") == ["assets/tausik-logo.png"]
    assert os.path.isfile(os.path.join(_ROOT, "docs", "assets", "tausik-logo-full.png"))


def test_a_made_up_asset_would_be_caught(tmp_path):
    """NEGATIVE: the resolver is a file check, not a regex on the page."""
    page = tmp_path / "x.md"
    page.write_text('<img src="assets/nope.png">', encoding="utf-8")
    src = _IMG.findall(page.read_text(encoding="utf-8"))[0]
    assert not os.path.isfile(os.path.join(str(tmp_path), src))
