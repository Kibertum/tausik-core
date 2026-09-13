"""The compaction contract names what must survive a context compaction — in both places.

Anthropic's own guidance: compaction can be instructed, and an uninstructed one
drops the "subtle context whose importance shows up later". Here that context
has names — a paid-for measurement, a retired rule — and losing either costs a
rerun or a resurrected dead rule. So the six items are listed by name in this
repository's CLAUDE.md and in the bootstrap template every consumer gets, and
this file fails the moment one of them disappears from either.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for sub in ("scripts", "bootstrap"):
    p = str(_REPO / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import bootstrap_templates as bt  # noqa: E402

# One marker per item, chosen so a paraphrase still matches but a dropped item does not.
_EN_ITEMS = {
    "active task": "active task and its slug",
    "scope + receipt": "verify receipt",
    "measurements": "measurements with their numbers",
    "retired rules": "superseded rules",
    "owner prohibitions": "Owner prohibitions",
    "open forks": "Open forks",
}
_RU_ITEMS = {
    "active task": "активную задачу и slug",
    "scope + receipt": "квитанцию verify",
    "measurements": "замеры сессии с числами",
    "retired rules": "отменённые правила",
    "owner prohibitions": "запреты владельца",
    "open forks": "открытые развилки",
}


def _body(tier: str) -> str:
    return bt.build_full_body("proj", ["python"], "agent", ".claude", context_tier=tier)


@pytest.mark.parametrize("item", sorted(_RU_ITEMS))
def test_this_repository_names_every_item(item):
    text = (_REPO / "CLAUDE.md").read_text(encoding="utf-8")
    static = text.split("<!-- DYNAMIC:START -->")[0]
    assert "## Компакция" in static
    assert _RU_ITEMS[item] in static, f"CLAUDE.md lost the compaction item: {item}"


@pytest.mark.parametrize("tier", ["standard", "full"])
@pytest.mark.parametrize("item", sorted(_EN_ITEMS))
def test_the_consumer_template_names_every_item(tier, item):
    body = _body(tier)
    assert "## Compaction contract" in body
    assert _EN_ITEMS[item] in body, f"{tier} tier lost the compaction item: {item}"


def test_the_minimal_tier_carries_the_pointer_not_the_list():
    """Negative: minimal stays minimal — one paragraph, no numbered contract."""
    body = _body("minimal")
    assert "## Compaction (minimal)" in body
    assert "## Compaction contract" not in body
    assert "1. **The active task" not in body
    for marker in ("active task and slug", "verify receipt", "open forks"):
        assert marker in body, f"minimal pointer lost: {marker}"


def test_the_contract_sits_after_memory_and_before_senar_rules():
    """Position is part of the contract: it is read as a memory rule, not as a footnote."""
    body = _body("standard")
    memory = body.index("## Memory (")
    contract = body.index("## Compaction contract")
    senar = body.index("## SENAR Rules Compliance")
    assert memory < contract < senar
