"""Every CI install of a verdict-deciding static tool goes through the pin file.

mypy-and-bandit-are-unpinned-in-ci-like-ruff-was: CI installed ruff, mypy and
bandit bare, so a lane's verdict depended on the release of the night before —
the ruff 0.15/0.16 skew on this machine already disagreed about formatting.
The pins live in ONE file, `ci-constraints.txt`; this test reads every install
line in the CI configs and the contributor guide and refuses a bare install.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = _ROOT / "ci-constraints.txt"
PINNED_TOOLS = ("ruff", "mypy", "bandit")
INSTALL_SOURCES = (
    ".github/workflows/tests.yml",
    ".github/workflows/security-review.yml",
    ".github/workflows/test-coverage.yml",
    ".gitlab-ci.yml",
    "CONTRIBUTING.md",
)
# This test reads CI configs as data; no import edge selects it.
CROSSCUTTING_SCOPE = [".github/", ".gitlab-ci.yml", "CONTRIBUTING.md", "ci-constraints.txt"]


def unpinned_installs(text: str) -> list[str]:
    """Install lines that name a pinned tool without `-c ci-constraints.txt`."""
    bad = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(("#", ">")) or "pip install" not in line:
            continue
        tokens = line.split("pip install", 1)[1].split()
        names = {re.split(r"[=<>~!\[]", t, maxsplit=1)[0].lower() for t in tokens}
        constrained = any(
            a in ("-c", "--constraint") and b.endswith("ci-constraints.txt")
            for a, b in zip(tokens, tokens[1:])
        )
        if names & set(PINNED_TOOLS) and not constrained:
            bad.append(line)
    return bad


def test_the_pin_file_pins_every_tool_exactly():
    pins = {}
    for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+)==(\S+)$", line.strip())
        if m:
            pins[m.group(1).lower()] = m.group(2)
    assert set(pins) == set(PINNED_TOOLS)


def _excluded_from_public_tree(rel: str) -> bool:
    sys.path.insert(0, str(_ROOT / "scripts"))
    from publication_snapshot import EXCLUDED_FROM_PUBLIC_SNAPSHOT

    return any(rel == e or rel.startswith(e) for e in EXCLUDED_FROM_PUBLIC_SNAPSHOT)


@pytest.mark.parametrize("rel", INSTALL_SOURCES)
def test_no_ci_install_of_a_pinned_tool_is_bare(rel):
    path = _ROOT / rel
    if not path.exists() and _excluded_from_public_tree(rel):
        pytest.skip(f"{rel} is excluded from the public snapshot; checked on the development line")
    assert path.exists(), f"{rel} is missing — the install paths cannot be checked"
    assert unpinned_installs(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "line, bare",
    [
        pytest.param("run: pip install ruff mypy bandit", True, id="bare"),
        pytest.param("pip install --quiet pytest mypy==1.0", True, id="inline-pin-is-not-the-file"),
        pytest.param("pip install -c ci-constraints.txt ruff", False, id="constrained"),
        pytest.param("pip install -r requirements.txt", False, id="no-tool"),
        pytest.param("# pip install ruff", False, id="comment"),
    ],
)
def test_the_reader_can_fail(line, bare):
    assert bool(unpinned_installs(line)) is bare
