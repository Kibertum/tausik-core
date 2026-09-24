"""An annotated CROSSCUTTING_SCOPE is a declaration, not silence
(annotated-crosscutting-scope-reads-as-undeclared)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_test_resolver import read_crosscutting_scope  # noqa: E402

CROSSCUTTING_SCOPE: list[str] = []  # this file itself uses the annotated form


def _file(tmp_path, body):
    p = tmp_path / "test_x.py"
    p.write_text(body, encoding="utf-8")
    return str(p)


@pytest.mark.parametrize(
    "body",
    ['CROSSCUTTING_SCOPE = ["docs/"]\n', 'CROSSCUTTING_SCOPE: list[str] = ["docs/"]\n'],
    ids=["assign", "annotated"],
)
def test_both_forms_read_the_same(tmp_path, body):
    assert read_crosscutting_scope(_file(tmp_path, body)) == ["docs/"]


def test_the_annotated_opt_out_is_an_empty_list(tmp_path):
    assert read_crosscutting_scope(_file(tmp_path, "CROSSCUTTING_SCOPE: list[str] = []\n")) == []


@pytest.mark.parametrize(
    "body",
    ["CROSSCUTTING_SCOPE: list[str]\n", "CROSSCUTTING_SCOPE: list[str] = make()\n"],
    ids=["annotation-only", "not-a-literal"],
)
def test_no_value_or_a_computed_value_is_still_undeclared(tmp_path, body):
    assert read_crosscutting_scope(_file(tmp_path, body)) is None
