"""The README's `--ide` list and its host table name every host bootstrap scaffolds.

Measured in session #251: both READMEs said `--ide claude|cursor|qwen|kilo`
while `SCAFFOLD_IDES` had carried `opencode` and `codex` for weeks, and the
support table filed Codex under "Windsurf / Codex-style … Expected / manual"
after a live Codex host had proved MCP, skills, agents and (under trusted
hooks) the native refusal. A host was added to the generator and nothing
required the front page to say so. The list is read from the README and
compared with the constant, in both languages, so the next host cannot arrive
in bootstrap without arriving on the page.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "bootstrap") not in sys.path:
    sys.path.insert(0, str(_ROOT / "bootstrap"))

from bootstrap_config import SCAFFOLD_IDES  # noqa: E402

CROSSCUTTING_SCOPE = ["README.md", "README.ru.md", "bootstrap/bootstrap_config.py"]

_READMES = {"en": _ROOT / "README.md", "ru": _ROOT / "README.ru.md"}
# The one place the front page spells the flag as a closed list.
_IDE_FLAG = re.compile(r"`--ide ((?:[a-z]+\|)+[a-z]+)`")
# The support table: a row per host, the host's name in the first cell.
_TABLE_ROW = re.compile(r"^\| \*?\*?([A-Za-z ]+?)\*?\*?(?: \(| \||$)", re.MULTILINE)
_ROW_NAMES = {
    "claude": "Claude Code",
    "cursor": "Cursor",
    "qwen": "Qwen Code",
    "kilo": "Kilo Code",
    "opencode": "OpenCode",
    "codex": "Codex CLI",
}


def _ide_list(text: str) -> list[str]:
    m = _IDE_FLAG.search(text)
    assert m, "the README no longer spells `--ide a|b|c` — the closed list this test reads"
    return m.group(1).split("|")


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_the_ide_flag_lists_exactly_the_scaffolded_hosts(lang):
    listed = _ide_list(_READMES[lang].read_text(encoding="utf-8"))
    assert listed == list(SCAFFOLD_IDES), (
        f"{lang}: README says `--ide {'|'.join(listed)}`, bootstrap scaffolds "
        f"{'|'.join(SCAFFOLD_IDES)} — a host missing from the page is a host nobody finds"
    )


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_every_scaffolded_host_has_a_row_in_the_support_table(lang):
    text = _READMES[lang].read_text(encoding="utf-8")
    rows = {m.group(1).strip() for m in _TABLE_ROW.finditer(text)}
    missing = [ide for ide, name in _ROW_NAMES.items() if name not in rows]
    assert not missing, f"{lang}: scaffolded host(s) without a support-table row: {missing}"
    assert "Codex-style" not in text and "Codex-подобные" not in text, (
        "Codex is scaffolded and live-verified; a 'Codex-style' catch-all row understates it"
    )


def test_the_row_names_cover_the_constant_and_nothing_else():
    """The mapping above is typed by hand; hold it to the constant it mirrors."""
    assert set(_ROW_NAMES) == set(SCAFFOLD_IDES)


def test_a_missing_host_is_caught(tmp_path):
    """Negative: a README that drops one scaffolded host reddens."""
    text = _READMES["en"].read_text(encoding="utf-8")
    listed = "|".join(SCAFFOLD_IDES)
    shorter = "|".join(i for i in SCAFFOLD_IDES if i != "opencode")
    assert f"`--ide {listed}`" in text
    mutated = text.replace(f"`--ide {listed}`", f"`--ide {shorter}`")
    assert _ide_list(mutated) != list(SCAFFOLD_IDES)
