"""Deterministic DB → Mermaid diagram-as-code renderer (graph-mermaid-render).

Borrowed from cubest's "one cube, many projections" idea: give the agent and a
human a diagram-as-code view of TAUSIK's graphs (native in artifacts, GitHub,
Obsidian). This module renders the memory/decision knowledge graph
(`memory_edges`) as a Mermaid flowchart.

Determinism mirrors the state export (byte-stable so a re-render never churns):
nodes are declared in sorted id order, edges sorted by
`(source, relation, target)`, and labels are sanitised to a Mermaid-safe subset
so no title/first-line ever breaks the diagram. Only live state travels
(non-archived memory, valid edges, slug-bearing nodes), matching the projection.

Read-only on the DB.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from slug_util import first_line

if TYPE_CHECKING:
    from project_service import ProjectService

_MAX_LABEL = 60
# Characters that break Mermaid node-label parsing even inside a quoted string;
# collapsed to a space. Quotes are handled separately (→ single quote).
_LABEL_UNSAFE = re.compile(r'[\[\]{}()<>|#;`"\\\r\n\t]+')


def _node_id(prefix: str, slug: str) -> str:
    """A Mermaid-safe node id: `m_`/`d_` + slug with hyphens as underscores.

    Slugs are `[a-z0-9-]`; the letter prefix guarantees the id never starts with
    a digit (a bare `2026-x` slug would), and `-`→`_` keeps Mermaid happy."""
    return f"{prefix}_{slug.replace('-', '_')}"


def _label(text: str, fallback: str) -> str:
    """Sanitise arbitrary text to a Mermaid-safe, single-line, bounded label."""
    raw = (text or "").strip() or fallback
    raw = _LABEL_UNSAFE.sub(" ", raw).replace('"', "'")
    raw = re.sub(r"\s+", " ", raw).strip()
    if len(raw) > _MAX_LABEL:
        raw = raw[: _MAX_LABEL - 1].rstrip() + "…"
    return raw or fallback


def render_memory_graph(svc: ProjectService) -> str:
    """Render the live memory/decision graph as a Mermaid `graph LR` flowchart.

    Includes only nodes that participate in a rendered edge (an isolated node
    adds noise to an edge view). An empty graph yields a valid, empty
    `graph LR` diagram. Byte-stable for a given DB state."""
    q = svc.be._q
    memory = q(
        "SELECT id, slug, title FROM memory "
        "WHERE archived_at IS NULL AND slug IS NOT NULL AND slug != ''"
    )
    decisions = q("SELECT id, slug, decision FROM decisions WHERE slug IS NOT NULL AND slug != ''")
    edges = q(
        "SELECT source_type, source_id, target_type, target_id, relation "
        "FROM memory_edges WHERE valid_to IS NULL"
    )

    nodes: dict[tuple[str, int], tuple[str, str]] = {}
    for m in memory:
        nodes[("memory", m["id"])] = (_node_id("m", m["slug"]), _label(m["title"], m["slug"]))
    for d in decisions:
        nodes[("decision", d["id"])] = (
            _node_id("d", d["slug"]),
            _label(first_line(d["decision"]), d["slug"]),
        )

    edge_rows: list[tuple[str, str, str]] = []
    used: set[str] = set()
    for e in edges:
        src = nodes.get((e["source_type"], e["source_id"]))
        tgt = nodes.get((e["target_type"], e["target_id"]))
        if not src or not tgt:
            continue  # dangling edge (target gone / slug-less) — skip, not crash
        edge_rows.append((src[0], e["relation"], tgt[0]))
        used.add(src[0])
        used.add(tgt[0])

    lines = ["graph LR"]
    label_by_id = {nid: lbl for nid, lbl in nodes.values()}
    for nid in sorted(used):
        lines.append(f'  {nid}["{label_by_id[nid]}"]')
    for esrc, rel, etgt in sorted(set(edge_rows)):
        lines.append(f"  {esrc} -->|{rel}| {etgt}")
    return "\n".join(lines) + "\n"
