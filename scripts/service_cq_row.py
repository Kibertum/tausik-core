"""cq knowledge-unit → memory-search display row.

Extracted from service_knowledge.py to keep that mixin under the 400-line
filesize cap (state-git-triggers added a post-write export hook that pushed it
over). ``CQ_SOURCE`` and ``build_cq_row`` are re-exported by service_knowledge so
existing callers and tests (``from service_knowledge import build_cq_row``) keep
working unchanged.
"""

from __future__ import annotations

from typing import Any

#: Marks a row in a memory-search result that came from cross-project `cq`
#: knowledge rather than this project's `memory` table.
CQ_SOURCE = "cq"


def build_cq_row(unit: dict[str, Any]) -> dict[str, Any]:
    """Render one cq knowledge unit as a memory-search result row.

    These rows are *display only* — they have no row in `memory` and therefore
    no address. They used to be emitted with ``id: 0``, which collided across
    every cq hit and pointed at a record that does not exist; a caller feeding
    a search result back into ``memory_show``/``memory_link`` got a confusing
    miss instead of a clear "not addressable". ``id`` is now ``None`` and
    ``source`` states the provenance, so consumers can branch on it explicitly.

    ``type`` stays ``"cq"`` as a display label. It is deliberately NOT one of
    ``VALID_MEMORY_TYPES``: nothing persists these rows, and a fake local type
    would be worse — it would make cross-project knowledge indistinguishable
    from this project's own.
    """
    # `or {}` rather than a .get() default: a network payload commonly carries
    # an explicit `"insight": null`, and a default only applies when the key is
    # ABSENT — so .get("insight", {}) still handed back None and the next
    # .get() raised AttributeError.
    insight = unit.get("insight") or {}
    evidence = unit.get("evidence") or {}
    conf = evidence.get("confidence") or 0
    return {
        "id": None,
        "source": CQ_SOURCE,
        "type": CQ_SOURCE,
        "title": f"[cq {conf:.0%}] {insight.get('summary', '')}",
        "content": insight.get("detail", ""),
        "tags": ",".join(unit.get("domain") or []),
    }
