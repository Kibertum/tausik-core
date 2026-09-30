"""The 1.9 charter document names the composition decision the map is built from.

Measured in session #251: `TAUSIK-plan-1.9.md` still said "basis of the
composition: decision #337" and "22 tasks" six days after #360 had superseded
#337 in so many words, and nothing compared the document with the journal. The
document's own preamble calls a plan describing a composition that no longer
exists "the exact defect this release is assembled to end — written about
itself". ROADMAP.md is generated and names the decision in force; this test
requires the plan's header note to name the same number, so the next
restatement cannot leave the charter document pointing at a retired one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import DORMANT_ON_PUBLIC_SNAPSHOT, IS_PUBLIC_SNAPSHOT

_ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(IS_PUBLIC_SNAPSHOT, reason=DORMANT_ON_PUBLIC_SNAPSHOT)

CROSSCUTTING_SCOPE = ["TAUSIK-plan-1.9.md", "ROADMAP.md"]

_MAP_BASIS = re.compile(r"Состав — из последнего решения[^#]*#(\d+)")
_PLAN_IN_FORCE = re.compile(r"(?:Действующий состав в силе|состав выпуска) — решение #(\d+)")
_MAP_VERSION = re.compile(r"^# Дорожная карта TAUSIK (\d+\.\d+)", re.M)
# The tag is published and cannot move (publishing.md), so the decision the
# release shipped with is a frozen fact of the journal, pinned here as such.
_SHIPPED_DECISION = 370
_SHIPPED_SENTENCE = "1.9 выпущена 14 сентября 2026 тегом v1.9.0"


def _map_version() -> str:
    text = (_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    m = _MAP_VERSION.search(text)
    assert m, "ROADMAP.md no longer names the version it maps"
    return m.group(1)


def _decision_in_force_per_map() -> int:
    text = (_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    m = _MAP_BASIS.search(text)
    assert m, "ROADMAP.md no longer names the decision its composition comes from"
    return int(m.group(1))


def _decision_in_force_per_plan(text: str) -> int:
    m = _PLAN_IN_FORCE.search(text)
    assert m, "TAUSIK-plan-1.9.md lost the header note naming the composition in force"
    return int(m.group(1))


def test_the_plan_names_the_decision_the_map_is_built_from():
    """While the map is the 1.9 map, the plan follows it; once the map belongs
    to a later version the plan is a dated record of a shipped release and
    holds the decision it shipped with instead (session #264: the 1.10
    composition moved the map and this test went red on a frozen document)."""
    plan = (_ROOT / "TAUSIK-plan-1.9.md").read_text(encoding="utf-8")
    if _map_version() == "1.9":
        assert _decision_in_force_per_plan(plan) == _decision_in_force_per_map(), (
            "the composition was restated (ROADMAP.md moved) and the charter document "
            "still points at the previous decision — update the header note"
        )
    else:
        assert _SHIPPED_SENTENCE in plan, "the plan does not say 1.9 shipped, or with which tag"
        assert _decision_in_force_per_plan(plan) == _SHIPPED_DECISION, (
            "the plan names a composition decision other than the one v1.9.0 shipped with"
        )


def test_the_plan_marks_its_september_7_composition_as_history():
    plan = (_ROOT / "TAUSIK-plan-1.9.md").read_text(encoding="utf-8")
    assert "#337 **отменено**" in plan
    assert "Состав на 7 сентября — историческая запись" in plan


def test_a_stale_number_in_the_plan_is_caught():
    """Negative: the note pointing at a retired decision reddens."""
    plan = (_ROOT / "TAUSIK-plan-1.9.md").read_text(encoding="utf-8")
    named = _decision_in_force_per_plan(plan)
    stale = plan.replace(f"— решение #{named}", "— решение #337", 1)
    assert _decision_in_force_per_plan(stale) == 337 != named
