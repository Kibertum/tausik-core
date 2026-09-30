"""What a compaction drops is on disk; the agent is told where.

MEASURED FIRST, AND IT REPLACED THE PLAN. The task asked for the full history to be
SAVED to a searchable file. It already is: the host writes a transcript, 36 MB for
one session of this project and 37 files in total, and `transcript_locator` finds
the current one BY PROOF rather than by guessing a directory name — the name is the
project path mangled, so guessing it was the defect that locator exists to fix.

So nothing needed saving. What was missing is that nobody told the agent. The
compaction contract listed six things to carry verbatim and said nothing about the
seventh question a reader has: where is everything else? Now Current State carries
the transcript's path and the contract points at it.

WHY THE PATH SITS IN THE VOLATILE HALF. Current State is rewritten every session
anyway, so a line there costs nothing in the invariant half of the instructions —
the half whose byte-stability `test_volatile_state_split` pins. Putting it among the
rules would have made the rules change every session.

THE LINE WAS PAID FOR. The generated file stood at 179 of its 180-line budget, so
the contract gained exactly one line and no blank: 180 on the nose. Following the
precedent set when 1.9 added the contract itself, the budget is spent, not moved.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _sub in ("scripts", "scripts/hooks", "bootstrap"):
    if str(_REPO / _sub) not in sys.path:
        sys.path.insert(0, str(_REPO / _sub))

import bootstrap_templates_tiers as tiers  # noqa: E402
import claudemd_state  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "bootstrap/"]


class TestTheContractNamesWhereTheRestIs:
    def test_the_seventh_item_points_at_the_transcript(self):
        assert "Where the rest is" in tiers.COMPACTION_CONTRACT
        assert "Current State" in tiers.COMPACTION_CONTRACT

    def test_it_says_to_grep_rather_than_re_derive(self):
        """Re-deriving a dropped measurement costs the run that produced it — the
        reason item 3 of the contract exists at all."""
        assert "Grep it rather than re-derive" in tiers.COMPACTION_CONTRACT

    def test_the_six_original_items_survive(self):
        """A seventh item that cost one of the six would be a worse contract."""
        for number in range(1, 7):
            assert f"{number}. **" in tiers.COMPACTION_CONTRACT

    def test_the_contract_stays_short(self):
        """A model given a one-line summarisation prompt wrote ~1k-token summaries
        with half the error of one given thousands of tokens of instruction. Length
        here is not neutral."""
        assert len(tiers.COMPACTION_CONTRACT.splitlines()) <= 11


class TestThePathIsResolvedByProofNotGuess:
    def test_the_helper_exists_and_is_used_by_the_state_block(self):
        source = (_REPO / "scripts" / "claudemd_state.py").read_text(encoding="utf-8")
        assert "_transcript_path(project_dir)" in source
        assert "Full history" in source

    def test_it_returns_a_real_file_on_this_tree(self):
        path = claudemd_state._transcript_path(str(_REPO))
        if path is None:
            pytest.skip("no host transcript for this project on this machine")
        # `~` РАСКРЫВАЕТСЯ, и проверяется именно это. Путь свёрнут к домашнему
        # каталогу нарочно: CLAUDE.md версионируется, а полное имя несёт имя
        # пользователя — гейт границы публикации поймал это на первой же записи.
        assert path.startswith("~"), "домашний каталог не свёрнут — имя пользователя уедет в git"
        resolved = Path(os.path.expanduser(path))
        assert resolved.is_file()
        assert resolved.suffix == ".jsonl"

    def test_a_directory_that_is_not_a_project_yields_none(self, tmp_path):
        """None rather than a guess: the previous rule in this area fell back to the
        most recently touched project ANYWHERE on the machine, which on Windows meant
        it never matched and always fell back."""
        assert claudemd_state._transcript_path(str(tmp_path)) is None

    def test_a_broken_locator_does_not_take_the_state_block_down(self, monkeypatch):
        """A hint must not cost a fresh agent its door into the project."""
        import transcript_locator

        def boom(*_a, **_kw):
            raise RuntimeError("locator exploded")

        monkeypatch.setattr(transcript_locator, "latest_project_transcript", boom)
        assert claudemd_state._transcript_path(str(_REPO)) is None


class TestTheDeployedStateBlockCarriesIt:
    @pytest.mark.parametrize("name", ["CLAUDE.md", "AGENTS.md"])
    def test_the_line_is_in_the_dynamic_block(self, name):
        path = _REPO / name
        if not path.is_file():
            pytest.skip(f"{name} absent")
        text = path.read_text(encoding="utf-8")
        if "<!-- DYNAMIC:START -->" not in text:
            pytest.skip(f"{name} carries no dynamic block")
        head, _, rest = text.partition("<!-- DYNAMIC:START -->")
        block, _, _ = rest.partition("<!-- DYNAMIC:END -->")
        if "Full history" not in text:
            pytest.skip("bootstrap has not re-run since the template changed")
        assert "Full history" in block, "the path leaked into the invariant half"
        assert "Full history" not in head


class TestTheLineBudgetWasPaidNotMoved:
    def test_the_generated_file_fits(self, tmp_path):
        from bootstrap_generate import generate_claude_md

        generate_claude_md(str(tmp_path), "proj", ["python"], "standard", "off")
        lines = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 180, (
            f"{len(lines)} lines — the budget is spent, not moved. Compress prose "
            "instead, as 1.9 did when it added this contract."
        )
