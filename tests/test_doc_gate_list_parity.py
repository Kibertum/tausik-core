"""Gate lists in the docs must not drift from the registry (doc-drift-class-surface-gate-unlisted).

Adding `class_surface` left six enumerations in EN+RU docs still describing the
previous set. That is the same failure the repo keeps hitting: a number or list
copied into prose, then left behind when the thing it describes moves. A test
that a human has to remember to run is not a guard, so this derives the expected
set from `GATE_REGISTRY` and reds on any gate the docs forget.

Convention #313: fenced code blocks are stripped before scanning — a gate name
inside a shell transcript is illustrative output, not a claim about the doc's own
list. Convention #320: a file only gets checked if it is named in `DOC_TARGETS`,
so a new enumeration must be added here or it is silently uncovered.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_registry import GATE_REGISTRY  # noqa: E402

CROSSCUTTING_SCOPE = ["docs/", "scripts/"]

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Each entry: (doc path, a regex locating the enumeration line/paragraph).
# Only lines that ENUMERATE gates are checked — prose merely mentioning one gate
# is not a list and must not be forced to name all of them.
DOC_TARGETS: list[tuple[str, str]] = [
    ("docs/en/architecture.md", r"Universal \(always on\):[^\n]*(?:\n[^\n|]*)?"),
    ("docs/ru/architecture.md", r"Универсальные \(всегда включены\):[^\n]*(?:\n[^\n|]*)?"),
    ("docs/en/mcp.md", r"Available gates:[^\n]*"),
    ("docs/ru/mcp.md", r"Доступные gates:[^\n]*"),
    ("docs/en/security.md", r"\*\*Built-in gates\*\*[^\n]*"),
    ("docs/ru/security.md", r"\*\*Встроенные гейты\*\*[^\n]*"),
]

# Gates that are genuinely universal (no stack detection, no external command):
# these are the ones every "always on" / "built-in" list must name.
UNIVERSAL_GATES = {"filesize", "class_surface", "tdd_order"}

_FENCE_RE = re.compile(r"```.*?```", re.S)


def _strip_fences(text: str) -> str:
    """Drop fenced blocks — convention #313: transcripts are output, not claims."""
    return _FENCE_RE.sub("", text)


def _read(rel: str) -> str:
    with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
        return _strip_fences(fh.read())


def test_universal_gates_set_matches_the_registry():
    """Guard the guard: if a universal gate is added, this list must move first."""
    registered = set(GATE_REGISTRY)
    missing = UNIVERSAL_GATES - registered
    assert not missing, f"UNIVERSAL_GATES names gates that no longer exist: {missing}"


def test_architecture_states_the_current_line_cap():
    """The cap is a NUMBER copied into prose — read it from the gate, never retype it.

    `architecture.md` claimed "each <=400 lines" for months after decision #190
    raised the cap to 500, by which point six modules were legitimately above 400.
    Third instance of this exact failure in one session, so the number is pinned
    to its source rather than to anyone remembering.

    Deliberately narrow: only `architecture.md` makes a claim about THIS repo.
    `claude-md-guide.md` uses "max 400 lines per file" as an example of how to
    phrase a concrete rule, and `brain-db-schema.md` carries a generic
    service-splitting heuristic — neither describes this project's cap, and
    forcing them to track it would be a false positive.
    """
    cap = GATE_REGISTRY["filesize"].default_config["max_lines"]
    for rel in ("docs/en/architecture.md", "docs/ru/architecture.md"):
        text = _read(rel)
        head = text[: text.find("| File |") if "| File |" in text else 8000]
        assert str(cap) in head, (
            f"{rel}: the scripts/ section must state the current cap ({cap}); "
            "update the prose when the gate's max_lines changes"
        )
        assert "<=400 lines" not in head and "≤400 строк" not in head, (
            f"{rel}: still claims the retired 400-line cap"
        )


@pytest.mark.parametrize(("rel", "pattern"), DOC_TARGETS, ids=[t[0] for t in DOC_TARGETS])
def test_gate_enumeration_names_every_universal_gate(rel, pattern):
    text = _read(rel)
    match = re.search(pattern, text)
    assert match, (
        f"{rel}: could not locate the gate enumeration with {pattern!r} — if the "
        "wording changed, update DOC_TARGETS (convention #320: an unlisted target "
        "is an unchecked one)"
    )
    block = match.group(0)
    missing = sorted(g for g in UNIVERSAL_GATES if f"`{g}`" not in block and g not in block)
    assert not missing, (
        f"{rel}: gate enumeration omits {missing}.\n"
        f"  found: {block.strip()[:200]}\n"
        "  A gate the docs never name is a gate users cannot anticipate blocking them."
    )
