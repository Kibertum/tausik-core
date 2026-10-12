"""Closed lists as CONSTANTS the docs are checked against — values, not just counts.

`constants.json` already carries the numbers docs quote (tools, hooks, stacks,
roles) so a stale copy fails `--check` instead of drifting. The VALUES of the
standard's closed lists were never in it, and the docs carry those too:
`docs/{en,ru}/mcp.md` spell the SPEC types, the ADAPT backward-finding
categories and the ADAPT lifecycle statuses out in full, slash-joined. Measured
in session #213: the SPEC line still described that list as it stood BEFORE
migration v49 — the two types ADR-013 added were absent from the values, and
the count written beside them was the old one — and nothing reddened, because
the guard that forbids a second literal list (`tests/closed_list_counts.py`,
`LIST_RE`) walks `scripts/`, `harness/` and `tests/` only. Documentation was
outside every closed-list control the project has.

(The numbers are deliberately not written here: this module is inside the tree
those guards walk, and a count beside a closed list is exactly what they
refuse — reformulating is the fix, an allow-list entry would not be.)

DERIVED, NEVER RE-TYPED. The values here come from the same tuples the service
layer and the DB CHECK constraints use, so this module cannot become the second
copy it exists to police — and the count travels as `len()`, so a widened list
updates the number without anyone writing one.

The doc side of the check lives in `doc_drift_scanners.scan_closed_list_enums`;
this module only says WHAT the closed lists are.
"""

from __future__ import annotations

from typing import Any

from service_adapts import ADAPT_STATUSES, FINDING_CATEGORIES
from service_specs import SPEC_TYPES

# Keyed by the constants.json entry name. `label` is what a drift message calls
# the subject, and the clause is named so a reader can go to the standard.
CLOSED_LISTS: dict[str, dict[str, Any]] = {
    "spec_types": {
        "label": "SPEC types (§13.3.4, ADR-013)",
        "values": list(SPEC_TYPES),
    },
    "adapt_finding_categories": {
        "label": "ADAPT backward-finding categories (§7.4.4)",
        "values": list(FINDING_CATEGORIES),
    },
    "adapt_statuses": {
        "label": "ADAPT lifecycle statuses (§7.8.1)",
        "values": list(ADAPT_STATUSES),
    },
}


def closed_lists_flat() -> dict[str, Any]:
    """Bundle for `gen_doc_constants` to merge into `constants.json`.

    One key, `closed_lists`, holding a mapping of name → {label, values}. Nested
    rather than flattened because the unit the doc check compares is the LIST:
    a flat `spec_types_count` would re-admit the shape this exists to remove —
    a number travelling apart from the values it counts.
    """
    return {"closed_lists": {k: dict(v) for k, v in CLOSED_LISTS.items()}}
