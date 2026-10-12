"""Every declared dependency must carry an upper version bound.

`mcp>=1.0.0` had a floor and no ceiling. TAUSIK builds `.tausik/venv` on the
user's machine at an unknown future moment, so an unbounded spec does not break
a build we would notice — it breaks their MCP server, quietly, the day a major
release lands.

SCOPE, so this is not mistaken for more: the check asserts an upper bound
EXISTS, not that it is well chosen. `<99.0.0` would satisfy it. This guards
against forgetting, not against a bad decision.

stdlib only — the project ships zero core dependencies, so the test that
protects that property may not import `packaging` to do its job.
"""

from __future__ import annotations

import os
import re

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REQUIREMENTS = os.path.join(_ROOT, "requirements.txt")

# name + the whole specifier tail, e.g. "mcp" / ">=1.0.0,<2.0.0"
_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$")
_UPPER = re.compile(r"(<|<=|==|~=)\s*\d")


def _requirement_lines() -> list[str]:
    """Lines that actually declare a requirement — not comments or pip options."""
    with open(_REQUIREMENTS, encoding="utf-8") as f:
        raw = f.read().splitlines()
    out = []
    for line in raw:
        stripped = line.split("#", 1)[0].strip()
        if not stripped or stripped.startswith("-"):
            continue
        out.append(stripped)
    return out


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", text))


class TestUpperBounds:
    def test_requirements_file_is_present_and_parsed(self):
        """Guard the guard: an empty parse must not pass vacuously."""
        assert os.path.isfile(_REQUIREMENTS)
        assert _requirement_lines(), "no requirements parsed — did the format change?"

    def test_every_requirement_has_an_upper_bound(self):
        unbounded = [line for line in _requirement_lines() if not _UPPER.search(line)]
        assert not unbounded, (
            "dependencies declared without an upper bound: "
            + ", ".join(unbounded)
            + ". A major release would install silently on the next bootstrap."
        )

    def test_mcp_range_admits_the_version_we_ship_against(self):
        """The bound must not exclude what is installed and working today."""
        spec = next(s for s in _requirement_lines() if s.startswith("mcp"))
        lo = re.search(r">=\s*([\d.]+)", spec)
        hi = re.search(r"<\s*([\d.]+)", spec)
        # Report the missing half instead of dying on None.group().
        assert lo, f"mcp requirement has no lower bound: {spec!r}"
        assert hi, f"mcp requirement has no upper bound: {spec!r}"
        installed = (1, 27, 0)
        assert _version_tuple(lo.group(1)) <= installed < _version_tuple(hi.group(1))


class TestParserPrecision:
    """A checker that cries wolf on comments would just get deleted."""

    @pytest.mark.parametrize(
        "line,is_requirement",
        [
            ("mcp>=1.0.0,<2.0.0", True),
            ("# just a comment", False),
            ("", False),
            ("   ", False),
            ("--index-url https://example.invalid", False),
            ("requests==2.0  # pinned hard", True),
        ],
    )
    def test_line_classification(self, line, is_requirement, tmp_path, monkeypatch):
        import test_requirements_bounds as mod

        f = tmp_path / "requirements.txt"
        f.write_text(line + "\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_REQUIREMENTS", str(f))
        assert bool(mod._requirement_lines()) is is_requirement

    @pytest.mark.parametrize(
        "spec,bounded",
        [
            ("mcp>=1.0.0", False),
            ("mcp>=1.0.0,<2.0.0", True),
            ("mcp==1.27.0", True),
            ("mcp~=1.27", True),
            ("mcp<=1.99", True),
            ("mcp", False),
        ],
    )
    def test_upper_bound_detection(self, spec, bounded):
        assert bool(_UPPER.search(spec)) is bounded
