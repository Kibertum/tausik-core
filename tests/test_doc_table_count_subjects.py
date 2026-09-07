"""Counted table columns, their subject registry, and what is declared unbound.

Measured in session #224 with `gen_doc_constants --check` GREEN the whole time:

* `AGENTS.md` carried three cells reading `**100** (93+7)` under the header
  "Main `tausik_*` tools (two servers)" — the same column as the row above,
  which read the correct `152 (145+7)` — three lines below a sentence promising
  that "canonical counts are asserted from `len(TOOLS)` in code".
* Both READMEs carried `21` in the `Hooks` / `Хуки` column against
  `hooks_count=22`, ten lines below prose saying `22` that WAS checked.

Neither header matched the single full-cell anchor the scan had, so no column
was located, so the scan passed. The defect is not the stale numbers — those
are a symptom that gets fixed one at a time — it is that a scanner which cannot
find its column reports SUCCESS. Every case below pins one half of the repair:
the registry that finds the columns, and the pairing with `constants.json` that
refuses to let a computed count exist with nobody checking it and nobody saying
so.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from doc_drift_common import (  # noqa: E402
    _CODE_COUNT_PATTERNS,
    _MCP_COUNT_PAIR_PATTERN,
    _MCP_COUNT_PATTERNS,
)
from doc_drift_tables import (  # noqa: E402
    TABLE_SUBJECT_EXEMPT,
    scan_table_count_columns,
    table_subject_keys,
)
from gen_doc_constants import build_constants_doc  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]

_PAYLOAD = {
    "mcp_main_tools": 152,
    "mcp_project_tools": 145,
    "mcp_brain_tools": 7,
    "hooks_count": 22,
    "skills_core_count": 13,
}


def _doc(tmp_path: Path, body: str, rel: str = "README.md") -> None:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# --- the two shapes that were live in the tree ---------------------------------

# Verbatim from AGENTS.md before the repair. Kept as a fixture rather than as a
# reference to the file: the file is now correct, and a regression pin that
# reads the current tree would pass for the wrong reason forever after.
_AGENTS_TABLE_BEFORE = (
    "| Model / host | Primary TAUSIK surface | Main `tausik_*` tools (two servers) | Notes |\n"
    "|---|---|---|---|\n"
    "| Claude (Code, VS Code Extension) | MCP | **152** (145+7) | Hooks + MCP |\n"
    "| Cursor / Composer / GPT-5.5+ | Same MCP | **100** (93+7) | self-serve |\n"
)

_README_TABLE_BEFORE = (
    "| IDE | MCP tools | Skills | Hooks | Status |\n"
    "|---|---|---|---|---|\n"
    "| **Claude Code** | 152 | 13 core + opt-in | 21 (full) | First-class |\n"
    "| **Cursor** | 152 | 13 core + opt-in | — (gates at task start/done) | Supported |\n"
    "| VSCode + Claude Extension | 152 | 13 core + opt-in | 21 | Tested E2E |\n"
)


def test_a_header_that_names_the_count_in_other_words_is_still_found(tmp_path):
    """The measured miss: the noun sits inside decoration, not alone in the cell."""
    _doc(tmp_path, _AGENTS_TABLE_BEFORE, rel="AGENTS.md")
    msgs = scan_table_count_columns(tmp_path, _PAYLOAD)
    assert any("AGENTS.md:4" in m and "'**100** (93+7)'" in m for m in msgs), msgs
    assert not any("AGENTS.md:3" in m for m in msgs), (
        "the correct row in the same column must stay quiet",
        msgs,
    )


def test_the_split_a_total_spells_out_is_checked_too(tmp_path):
    """`(93+7)` is two more claims, and both were wrong while the scan was green."""
    _doc(tmp_path, _AGENTS_TABLE_BEFORE, rel="AGENTS.md")
    msgs = scan_table_count_columns(tmp_path, _PAYLOAD)
    assert any("split '(93+7)'" in m and "mcp_project_tools=145" in m for m in msgs), msgs


def test_several_counted_columns_in_one_table_are_all_read(tmp_path):
    """The IDE table counts tools, skills and hooks side by side.

    The predecessor stopped at the first header it recognised, so a second
    counted column in the same table was never reached.
    """
    _doc(tmp_path, _README_TABLE_BEFORE, rel="README.md")
    msgs = scan_table_count_columns(tmp_path, _PAYLOAD)
    hooks = [m for m in msgs if "hook-count" in m]
    assert len(hooks) == 2, msgs
    assert "README.md:3" in hooks[0] and "'21 (full)'" in hooks[0]
    assert "README.md:5" in hooks[1] and "'21'" in hooks[1]
    assert not any("core-skill-count" in m or "MCP tool-count" in m for m in msgs), (
        "the honest columns in the same table must stay quiet",
        msgs,
    )


def test_a_parenthetical_gloss_is_read_but_a_decoration_is_not(tmp_path):
    """A gloss leaves the count alone; a decoration changes what it claims.

    "21 (full)" asserts 21 exactly, while "21+" and "~21" assert something this
    column has no convention for. The line between them is what is GLUED to the
    number — the same reason recorded for the predecessor, external review #40.
    """
    table = "| IDE | Hooks |\n|---|---|\n| a | 21+ |\n| b | ~21 |\n| c | 21 (full) |\n"
    _doc(tmp_path, table, rel="README.md")
    msgs = scan_table_count_columns(tmp_path, _PAYLOAD)
    assert len(msgs) == 1 and "README.md:5" in msgs[0], msgs


def test_the_header_is_the_first_row_not_whichever_row_matches(tmp_path):
    """NEGATIVE SCENARIO: a data cell reading like a header must not take over.

    Locating the header by "first row that matches a subject" would let the body
    of a table redefine the column halfway down, and the numbers after that point
    would be read against the wrong constant — a false RED, which costs more
    trust than the silence this scan exists to end.
    """
    impostor = "| Gate | Severity |\n|---|---|\n| filesize | 500 |\n| Hooks | 21 |\n"
    _doc(tmp_path, impostor, rel="README.md")
    assert scan_table_count_columns(tmp_path, _PAYLOAD) == []

    # The same stale 21 under a REAL header is read, so the silence above is a
    # statement about where the header is — not a scan that was asleep. Pinned
    # in one case on purpose: a quiet assertion standing alone cannot tell those
    # two apart, which is the exact failure this whole module was written for.
    honest = "| Gate | Hooks |\n|---|---|\n| filesize | 21 |\n"
    _doc(tmp_path, honest, rel="README.md")
    msgs = scan_table_count_columns(tmp_path, _PAYLOAD)
    assert len(msgs) == 1 and "README.md:3" in msgs[0], msgs


def test_a_missing_constant_disables_that_column_rather_than_crashing(tmp_path):
    _doc(tmp_path, _README_TABLE_BEFORE, rel="README.md")
    assert scan_table_count_columns(tmp_path, {}) == []


def test_an_unscanned_file_is_not_read(tmp_path):
    """Only the declared targets are scanned; a stray doc is nobody's claim."""
    _doc(tmp_path, _README_TABLE_BEFORE, rel="docs/en/scratch.md")
    assert scan_table_count_columns(tmp_path, _PAYLOAD) == []


# --- the meta-hole: a computed count with nobody checking it -------------------


def _prose_bound_keys() -> set[str]:
    """Constants keys some prose pattern compares a document against."""
    keys = {key for _pattern, key, _label in _MCP_COUNT_PATTERNS}
    keys |= set(_MCP_COUNT_PAIR_PATTERN[1])
    keys |= {key for _pattern, key, _label in _CODE_COUNT_PATTERNS}
    # test_count has its own pattern table, whose entries carry a label instead
    # of a key because every one of them compares against the same constant.
    keys.add("test_count")
    keys.add("tausik_version")
    return keys


def test_every_computed_count_is_either_bound_or_declared_unbound():
    """The hole one level above the stale numbers.

    Two constants — `mcp_rag_tools` and `mcp_tools_with_optional_rag` — existed
    with NOTHING in any document checked against either, which is how AGENTS.md
    went on promising "+7 tools → **107** total" after the total reached 159.
    Nobody had to be careless for that: adding a constant and binding a document
    to it were separate acts, and only one of them was enforced. This pairs them.
    """
    payload = build_constants_doc(_REPO_ROOT)
    computed = {k for k, v in payload.items() if isinstance(v, int)}
    accounted = table_subject_keys() | set(TABLE_SUBJECT_EXEMPT)
    assert computed <= accounted, (
        "these computed counts are checked by nothing and declared nowhere: "
        f"{sorted(computed - accounted)}"
    )


def test_an_exemption_states_a_reason_and_does_not_contradict_a_subject():
    for key, reason in TABLE_SUBJECT_EXEMPT.items():
        assert reason.strip(), f"{key} is exempt with no reason given"
        assert key not in table_subject_keys(), (
            f"{key} is both a table subject and declared exempt from being one"
        )


@pytest.mark.parametrize("key", sorted(set(TABLE_SUBJECT_EXEMPT) - {"schema_version"}))
def test_exempt_from_a_column_never_means_exempt_from_every_check(key):
    """`schema_version` is the ONE constant no document quotes, and it is named.

    Every other exemption says the count lives in prose rather than in a column;
    this asserts that the prose really does check it, so "exempt" can never
    quietly become "unchecked".
    """
    assert key in _prose_bound_keys(), (
        f"{key} is exempt from the column scan and bound by no prose pattern either"
    )


def test_the_live_tree_is_clean():
    """The repository itself, after the measured cells were corrected."""
    assert scan_table_count_columns(_REPO_ROOT, build_constants_doc(_REPO_ROOT)) == []
