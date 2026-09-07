"""Closed lists and tool-count table cells in the docs, checked against constants.

Two blind spots measured in session #213 and closed here:

* The docs SPELL OUT the standard's closed lists (SPEC types, ADAPT
  backward-finding categories, ADAPT lifecycle statuses), and the guard that
  forbids a second literal copy walks `scripts/`, `harness/`, `tests/` only.
  `docs/{en,ru}/mcp.md` had gone on describing the SPEC type list as it stood
  before migration v49 widened it, values and count alike, and nothing
  reddened. (Numbers are not written out in this file: it sits inside the tree
  the count guards walk, and a count beside a closed list is what they refuse.)
* A bare markdown table cell (`| 128 |`) carries no word for the MCP-count
  patterns to anchor on, so README.md's five IDE-table cells were unchecked
  while the prose two lines below them was not. (The column scan grew a
  subject registry in session #224 — its own cases live in
  `test_doc_table_count_subjects.py`; what stays here is the behaviour that
  was already pinned when it guarded a single subject.)

Every negative case below is a doc that LIES in one specific way; the positive
ones pin that the scanners stay quiet on honest text, on fenced illustrations,
and on enumerations that are not one of our lists at all.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from doc_closed_lists import CLOSED_LISTS, closed_lists_flat  # noqa: E402
from doc_drift_scanners import (  # noqa: E402
    CROSS_FILE_SCAN_TARGETS,
    scan_closed_list_enums,
    scan_table_count_columns,
)
from service_adapts import ADAPT_STATUSES, FINDING_CATEGORIES  # noqa: E402
from service_specs import SPEC_TYPES  # noqa: E402

_PAYLOAD = {**closed_lists_flat(), "mcp_main_tools": 128}

_SPEC_LINE = "`type` is a closed list of {n} ({values}); a new type amends the standard"


def _doc(tmp_path, body: str, rel: str = "docs/en/mcp.md"):
    assert rel in CROSS_FILE_SCAN_TARGETS
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _spec_doc(tmp_path, values, n=None):
    _doc(tmp_path, _SPEC_LINE.format(n=len(values) if n is None else n, values="/".join(values)))


# --- the values ---------------------------------------------------------------


def test_the_lists_are_derived_from_the_service_tuples():
    """No second literal copy: the constants ARE the source tuples."""
    assert CLOSED_LISTS["spec_types"]["values"] == list(SPEC_TYPES)
    assert CLOSED_LISTS["adapt_finding_categories"]["values"] == list(FINDING_CATEGORIES)
    assert CLOSED_LISTS["adapt_statuses"]["values"] == list(ADAPT_STATUSES)


def test_the_live_constants_actually_carry_the_lists():
    """The guard is only armed while `constants.json` holds the lists.

    Written because a declared mutation SURVIVED: dropping
    `closed_lists_flat()` from `build_constants_doc` left every doc test green,
    because a payload without the key degrades the scanner to silence — by
    design, so a fresh checkout does not explode, and therefore exactly the
    shape that hides the disarming. `--check` catches it only while
    `constants.json` on disk still has the key; regenerate both and the guard
    is gone with nothing red. This asserts the payload itself.
    """
    from pathlib import Path

    from gen_doc_constants import build_constants_doc

    payload = build_constants_doc(Path(__file__).resolve().parents[1])
    lists = payload.get("closed_lists")
    assert isinstance(lists, dict), "constants carry no closed lists — the doc guard is disarmed"
    assert set(lists) == set(CLOSED_LISTS), lists
    for name, spec in lists.items():
        assert spec["values"], f"{name}: no values"
        assert spec["label"], f"{name}: no label for a drift message to name"


def test_an_honest_enumeration_is_silent(tmp_path):
    _spec_doc(tmp_path, list(SPEC_TYPES))
    assert scan_closed_list_enums(tmp_path, _PAYLOAD) == []


def test_a_missing_value_is_named(tmp_path):
    """AC-2(г) — the live defect: the pre-v49 values, with a count that agrees
    with them and not with the list."""
    older = [t for t in SPEC_TYPES if t not in ("TEST", "DOC")]
    _spec_doc(tmp_path, older, n=len(older))
    msgs = scan_closed_list_enums(tmp_path, _PAYLOAD)
    assert msgs, "a doc quoting a subset of the types must not pass"
    assert "missing ['TEST', 'DOC']" in msgs[0]
    assert any(
        f"closed list of {len(older)}" in m and f"holds {len(SPEC_TYPES)}" in m for m in msgs
    ), msgs


def test_an_unknown_value_is_named(tmp_path):
    """AC-2(в): a local type nobody amended the standard for."""
    _spec_doc(tmp_path, [*SPEC_TYPES, "FOO"])
    msgs = scan_closed_list_enums(tmp_path, _PAYLOAD)
    assert msgs and "unknown ['FOO']" in msgs[0], msgs


def test_the_right_values_with_a_wrong_count_still_reds(tmp_path):
    """AC-2(б): the number and the values are ONE claim, judged together."""
    understated = len(SPEC_TYPES) - 2
    _spec_doc(tmp_path, list(SPEC_TYPES), n=understated)
    msgs = scan_closed_list_enums(tmp_path, _PAYLOAD)
    assert len(msgs) == 1, msgs
    assert f"closed list of {understated}" in msgs[0] and f"holds {len(SPEC_TYPES)}" in msgs[0]


def test_a_renamed_value_reds_as_both_missing_and_unknown(tmp_path):
    """The ADAPT rename that reached the docs by hand in #210 (signed→approved)."""
    _doc(
        tmp_path,
        "status (closed list: "
        + "/".join("signed" if s == "approved" else s for s in ADAPT_STATUSES)
        + ")",
    )
    msgs = scan_closed_list_enums(tmp_path, _PAYLOAD)
    assert msgs and "missing ['approved']" in msgs[0] and "unknown ['signed']" in msgs[0], msgs


def test_the_finding_categories_are_watched_too(tmp_path):
    _doc(
        tmp_path,
        f"`category` is a closed list of {len(FINDING_CATEGORIES)} ("
        + "/".join(FINDING_CATEGORIES[:-1])
        + ")",
    )
    msgs = scan_closed_list_enums(tmp_path, _PAYLOAD)
    assert msgs and "backward-finding" in msgs[0], msgs


def test_a_lowercase_quotation_is_still_our_list(tmp_path):
    """NEGATIVE SCENARIO, found by external review #40 and reproduced.

    Overlap was computed case-sensitively, so a doc spelling the list in
    another case scored zero, fell below the floor and was skipped ENTIRELY —
    content drift inside it was invisible. A doc may quote the list in any
    case; what it may not do is quote a different list.
    """
    lower = [t.lower() for t in SPEC_TYPES]
    _spec_doc(tmp_path, lower)
    assert scan_closed_list_enums(tmp_path, _PAYLOAD) == [], "a full quotation, lowercased"
    _spec_doc(tmp_path, [t for t in lower if t not in ("test", "doc")], n=len(lower) - 2)
    msgs = scan_closed_list_enums(tmp_path, _PAYLOAD)
    assert msgs, "drift inside a lowercased quotation must still be caught"
    assert "missing ['TEST', 'DOC']" in msgs[0]


def test_a_decorated_cell_is_a_declared_exclusion(tmp_path):
    """AC-5: '128+' is skipped BY DECISION, and the docstring says why.

    Pinned so the exclusion is visible and testable rather than an accident of
    `isdigit()`: this column has no lower-bound convention (test_count has one,
    decision #182), and inventing one inside a scanner would be policy written
    where nobody looks for it.
    """
    from doc_drift_scanners import scan_table_count_columns as scan

    _doc(tmp_path, _TABLE.format(a="128+", b="~121"), rel="README.md")
    assert scan(tmp_path, _PAYLOAD) == []
    assert "declared exclusion" in " ".join((scan.__doc__ or "").split()), (
        "the exclusion must be stated where the next reader meets it"
    )


def test_an_unrelated_slash_run_is_not_one_of_our_lists(tmp_path):
    """NEGATIVE SCENARIO: the subject is derived by overlap, so a path or an
    unrelated enumeration must not be dragged in and reported as drift."""
    _doc(tmp_path, "See harness/claude/mcp/project for the layout; a/b/c/d is not a list.\n")
    assert scan_closed_list_enums(tmp_path, _PAYLOAD) == []


def test_two_shared_values_are_coincidence_not_a_quotation(tmp_path):
    """The overlap floor: `draft/review` plus a stranger is prose, not the list."""
    _doc(tmp_path, "The flow is draft/review/merge for ordinary work.\n")
    assert scan_closed_list_enums(tmp_path, _PAYLOAD) == []


def test_a_fenced_illustration_is_ignored(tmp_path):
    _doc(tmp_path, "```\nARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS\n```\n")
    assert scan_closed_list_enums(tmp_path, _PAYLOAD) == []


def test_an_empty_registry_disables_the_scan(tmp_path):
    """Degrades to silence, never to a crash, if constants carry no lists."""
    _spec_doc(tmp_path, [t for t in SPEC_TYPES if t != "DOC"])
    assert scan_closed_list_enums(tmp_path, {"closed_lists": {}}) == []
    assert scan_closed_list_enums(tmp_path, {}) == []


# --- the table cells -----------------------------------------------------------


_TABLE = """| IDE | MCP tools | Skills |
|---|---|---|
| **Claude Code** | {a} | 13 core |
| **Cursor** | {b} | 13 core |
| Windsurf | MCP + rules | host-dependent |
"""


def test_matching_cells_are_silent(tmp_path):
    _doc(tmp_path, _TABLE.format(a=128, b=128), rel="README.md")
    assert scan_table_count_columns(tmp_path, _PAYLOAD) == []


def test_a_stale_cell_is_named_with_its_line(tmp_path):
    """AC-4 negative: one cell left behind is the whole point of this scanner."""
    _doc(tmp_path, _TABLE.format(a=128, b=121), rel="README.md")
    msgs = scan_table_count_columns(tmp_path, _PAYLOAD)
    assert len(msgs) == 1, msgs
    assert "README.md:4" in msgs[0] and "'121'" in msgs[0] and "mcp_main_tools=128" in msgs[0]


def test_a_non_numeric_cell_is_not_a_count(tmp_path):
    """'MCP + rules' is honest prose in that column, not a stale number."""
    _doc(tmp_path, _TABLE.format(a=128, b=128), rel="README.md")
    assert scan_table_count_columns(tmp_path, _PAYLOAD) == []


def test_the_column_is_found_by_its_header_not_its_position(tmp_path):
    """NEGATIVE SCENARIO: insert a column ahead of it and the check must follow
    the header, not go on reading index 1 (which now holds the Skills count)."""
    body = (
        "| IDE | Skills | MCP tools |\n|---|---|---|\n"
        "| **Claude Code** | 13 | 121 |\n| **Cursor** | 13 | 128 |\n"
    )
    _doc(tmp_path, body, rel="README.md")
    msgs = scan_table_count_columns(tmp_path, _PAYLOAD)
    assert len(msgs) == 1, msgs
    assert "'121'" in msgs[0], "the moved column must be read, and 13 must not be"


def test_a_second_table_without_the_column_is_not_scanned(tmp_path):
    """The column index does not leak past the end of its own table."""
    body = (
        "| IDE | MCP tools |\n|---|---|\n| **Claude Code** | 128 |\n\n"
        "| Gate | Severity |\n|---|---|\n| filesize | 500 |\n"
    )
    _doc(tmp_path, body, rel="README.md")
    assert scan_table_count_columns(tmp_path, _PAYLOAD) == []


def test_no_expected_count_disables_the_scan(tmp_path):
    _doc(tmp_path, _TABLE.format(a=999, b=999), rel="README.md")
    assert scan_table_count_columns(tmp_path, {}) == []


# --- the live tree -------------------------------------------------------------


@pytest.mark.parametrize("scan", [scan_closed_list_enums, scan_table_count_columns])
def test_the_live_docs_are_clean(scan):
    """The repository itself, after the SPEC-type line was corrected."""
    from pathlib import Path

    from gen_doc_constants import build_constants_doc

    root = Path(__file__).resolve().parents[1]
    assert scan(root, build_constants_doc(root)) == []
