"""Every change of RENAR 1.1 is done, declared or deferred — never silent
(renar-11-remaining-deltas-are-declared-not-silently-missing)."""

from __future__ import annotations

import importlib
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import renar_v11_deltas as d11  # noqa: E402
from conftest import canonical_schema_db  # noqa: E402
from renar_standard_drift import corpus_root  # noqa: E402

CROSSCUTTING_SCOPE = ["docs/en/renar-11-deltas.md", "docs/ru/renar-11-deltas.md"]


def _resolve(ref: str):
    module, func = ref.split(":")
    return getattr(importlib.import_module(module), func)


def test_the_registry_has_exactly_the_rows_of_the_guide():
    root = corpus_root()
    if root is None:
        pytest.skip("no RENAR corpus configured on this machine (renar_standard_corpus)")
    assert d11.guide_rows(root) == [d["row"] for d in d11.DELTAS]


def test_the_registry_as_it_stands_is_valid():
    assert d11.validate(d11.DELTAS) == []


def test_implemented_without_a_mechanism_is_refused():
    bad = [{"row": 99, "change": "x", "status": "implemented"}]
    assert d11.validate(bad) and "mechanism" in d11.validate(bad)[0]
    bad = [{"row": 99, "change": "x", "status": "implemented", "mechanism": "nowhere:nothing"}]
    assert d11.validate(bad) and "does not resolve" in d11.validate(bad)[0]


def test_inapplicable_without_a_premise_and_deferred_without_a_decision_are_refused():
    assert d11.validate([{"row": 98, "change": "x", "status": "inapplicable"}])
    assert d11.validate([{"row": 97, "change": "x", "status": "deferred", "to": "2.0"}])
    assert d11.validate([{"row": 96, "change": "x", "status": "adopted-ish"}])


@pytest.mark.parametrize(
    "delta",
    [d for d in d11.DELTAS if d["status"] == "inapplicable"],
    ids=lambda d: f"row{d['row']}",
)
def test_each_inapplicability_premise_holds_on_the_fresh_schema(delta):
    """The ratchet: the day a carrier appears, the declaration must be re-decided."""
    conn = canonical_schema_db()
    try:
        assert _resolve(delta["premise_check"])(conn) == ()
    finally:
        conn.close()


def test_a_carrier_appearing_breaks_its_premise():
    conn = canonical_schema_db()
    try:
        conn.execute("CREATE TABLE manual_walkthroughs (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE components (id INTEGER PRIMARY KEY, uses TEXT)")
        conn.execute("CREATE TABLE ui_specs (id INTEGER PRIMARY KEY, screens TEXT)")
        conn.execute(
            "CREATE TABLE reviews_ar (id INTEGER PRIMARY KEY, tz_ref TEXT, verdict TEXT, "
            "produces_adapt TEXT, status TEXT)"
        )
        assert d11.manual_walkthrough_carriers(conn) == ("manual_walkthroughs",)
        assert d11.component_carriers(conn) == ("components",)
        assert "ui_specs" in d11.screen_carriers(conn)
    finally:
        conn.close()


def test_the_manifest_publishes_every_declared_and_deferred_row():
    sec = d11.section()
    rows = {r["row"] for r in sec["declared-inapplicable"]} | {r["row"] for r in sec["deferred"]}
    expected = {d["row"] for d in d11.DELTAS if d["status"] in ("inapplicable", "deferred")}
    assert rows == expected
    assert all(r["premise"] and r["premise-watched-by"] for r in sec["declared-inapplicable"])


def test_the_committed_manifest_carries_the_block():
    with open(os.path.join(_ROOT, "RENAR-CONFORMANCE.yaml"), encoding="utf-8") as f:
        text = f.read()
    assert "renar-11-deltas:" in text
    for d in d11.DELTAS:
        if d["status"] == "inapplicable":
            assert d["premise_check"] in text


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_the_page_lists_every_row_with_its_status(lang):
    with open(os.path.join(_ROOT, "docs", lang, "renar-11-deltas.md"), encoding="utf-8") as f:
        lines = f.read().splitlines()
    for d in d11.DELTAS:
        row = [ln for ln in lines if ln.startswith(f"| {d['row']} |")]
        assert len(row) == 1, d["row"]
        assert f"`{d['status']}`" in row[0], d["row"]


def test_the_manifest_names_the_declared_senar_edition():
    """The manifest carried senar-version 1.3 after the claim moved to 1.5."""
    from renar_conformance import SENAR_VERSION
    from senar_version_claim import DECLARED_SENAR_VERSION

    assert SENAR_VERSION == DECLARED_SENAR_VERSION
    with open(os.path.join(_ROOT, "RENAR-CONFORMANCE.yaml"), encoding="utf-8") as f:
        assert f"senar-version: '{DECLARED_SENAR_VERSION}'" in f.read()
