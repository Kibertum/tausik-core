"""Writing project state must not move a byte of the instructions around it.

WHY THIS MATTERS MORE THAN IT LOOKS. Session #277 measured cache_read at 99.5% of
all input across 5964 recorded calls — the spend is almost entirely the prefix
being re-sent, about half a million tokens per call. A prefix that changes is a
prefix that is re-read at full price, so which bytes move when state is written is
a cost question, not a tidiness one.

WHAT WAS MEASURED, AND IT NARROWED THE TASK. The DYNAMIC block is 3320 of 6377
characters in CLAUDE.md (52%) and 2231 of 14901 in AGENTS.md (14%), and the file
changes on nearly every commit. But the invariant half ALREADY does not move:
running `update-claudemd` after a state change leaves the bytes before and after
the markers byte-identical. So the separation this file guards exists; what does
not exist is any way for a project file to tell the host to place the volatile half
after a cache boundary. Claude Code offers no import or boundary directive a
project can set, so that half of the idea is a finding rather than code.

This file therefore pins the property that IS true, so that a future edit cannot
start rewriting whole files and silently turn every session into a cold prefix.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import claudemd_writer as writer  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/claudemd_writer.py", "scripts/claudemd_state.py"]

_START = "<!-- DYNAMIC:START -->"
_END = "<!-- DYNAMIC:END -->"


def _thirds(text: str) -> tuple[str, str, str]:
    """`(before marker, block, after marker)`. Raises when a marker is missing."""
    head = text.index(_START)
    tail = text.index(_END)
    return text[:head], text[head:tail], text[tail:]


def _digest(chunk: str) -> str:
    return hashlib.sha256(chunk.encode("utf-8")).hexdigest()


def _file(tmp_path: Path, block: str = "old state") -> Path:
    path = tmp_path / "CLAUDE.md"
    path.write_text(
        f"# CLAUDE.md\n\n## Hard Constraints\n\n- a rule that must not move\n\n"
        f"{_START}\n{block}\n{_END}\n\n## Reference\n\nsee docs\n",
        encoding="utf-8",
    )
    return path


class TestOnlyTheBlockMoves:
    """The property that makes the instruction half cacheable at all."""

    def test_the_bytes_before_and_after_the_markers_are_identical(self, tmp_path):
        path = _file(tmp_path)
        before = _thirds(path.read_text(encoding="utf-8"))
        writer.apply_dynamic_section(str(path), "brand new state, longer than before", False)
        after = _thirds(path.read_text(encoding="utf-8"))
        assert _digest(after[0]) == _digest(before[0]), "text before the marker moved"
        assert _digest(after[2]) == _digest(before[2]), "text after the marker moved"

    def test_the_block_itself_does_change(self, tmp_path):
        """The premise. If the block were also untouched, the test above would be
        green for the wrong reason — nothing was written at all."""
        path = _file(tmp_path)
        before = _thirds(path.read_text(encoding="utf-8"))
        writer.apply_dynamic_section(str(path), "brand new state", False)
        assert _digest(_thirds(path.read_text(encoding="utf-8"))[1]) != _digest(before[1])

    @pytest.mark.parametrize(
        "block",
        [
            pytest.param("", id="emptied"),
            pytest.param("a" * 4000, id="much_longer"),
            pytest.param("строка\nдругая\n", id="multiline_cyrillic"),
        ],
    )
    def test_the_surroundings_survive_any_block(self, tmp_path, block):
        path = _file(tmp_path)
        before = _thirds(path.read_text(encoding="utf-8"))
        writer.apply_dynamic_section(str(path), block, False)
        after = _thirds(path.read_text(encoding="utf-8"))
        assert (_digest(after[0]), _digest(after[2])) == (_digest(before[0]), _digest(before[2]))

    def test_a_dry_run_writes_nothing_at_all(self, tmp_path):
        path = _file(tmp_path)
        before = _digest(path.read_text(encoding="utf-8"))
        writer.apply_dynamic_section(str(path), "would-be state", True)
        assert _digest(path.read_text(encoding="utf-8")) == before


class TestAFileWithoutMarkersIsLeftAlone:
    """A hand-written instruction file is somebody's own text, not our canvas."""

    def test_nothing_is_written_and_the_skip_is_named(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        path.write_text("# mine\n\nno markers here\n", encoding="utf-8")
        before = _digest(path.read_text(encoding="utf-8"))
        message, changed = writer.apply_dynamic_section(str(path), "state", False)
        assert changed is False
        assert _digest(path.read_text(encoding="utf-8")) == before
        assert "marker not found" in message


class TestTheLiveTreeHasTheProperty:
    """Measured on the repository's own files, because a property that holds only
    in a fixture holds where it costs nothing."""

    @pytest.mark.parametrize("name", ["CLAUDE.md", "AGENTS.md"])
    def test_the_block_is_delimited_and_a_minority_of_nothing_else(self, name):
        path = _REPO / name
        if not path.is_file():
            pytest.skip(f"{name} is not present in this tree")
        text = path.read_text(encoding="utf-8")
        if _START not in text:
            pytest.skip(f"{name} carries no DYNAMIC block")
        head, block, tail = _thirds(text)
        assert head and tail, "the block swallowed the whole file"
        assert len(block) < len(text), "nothing invariant left to cache"
