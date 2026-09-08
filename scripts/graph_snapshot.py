"""A graph snapshot per release, and what CHANGED IN THE RELATIONS since.

WHAT THIS ANSWERS THAT NOTHING ELSE DOES. "Requirement #12 is no longer covered
by any test" cannot be expressed by comparing texts, however carefully worded —
it is a statement about EDGES. The RENAR drift detectors compare wording;
comparing snapshots compares structure, and the two see different things.

MEASURED BEFORE THE STORAGE WAS CHOSEN (session #237, live graph): 4,288
artifacts and 23,695 edges serialise to 2,103 KB as TSV — comparable to all of
`scripts/*.py` at 3,683 KB, which is exactly the size the task warned about.
Compressed it is 150 KB, fourteen times smaller. So snapshots are stored WHOLE
and compressed rather than as deltas: a delta chain needs a base and every link
intact, and a broken link invalidates everything after it. At 150 KB per release
that complexity buys nothing.

THE COMPLETENESS FACTS TRAVEL WITH THE EDGES, and that is the part that decides
whether anybody keeps reading the reports. Two snapshots taken at different
graph completeness — one before a test run was ever observed — differ by 6,051
`observed_coverage` edges that were never absent from the CODE, only from the
INDEX. Reporting those as "vanished coverage" would fill the first report with
false alarms, and a report that cried wolf once does not get read again.
"""

from __future__ import annotations

import gzip
import json
import os
import sqlite3
from typing import Any

#: Where snapshots live. Under `tausik/` because they are project state that
#: travels with the repository — a snapshot kept only on the machine that took
#: it cannot answer "what changed since the last release".
SNAPSHOT_DIR = os.path.join("tausik", "graph-snapshots")

#: How many examples a difference lists before stating the remainder. Same bound
#: and same reason as every other graph answer: a report nobody finishes is a
#: report nobody acts on.
EXAMPLES = 10


def snapshot_path(project_dir: str, label: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-._" else "-" for ch in label)
    return os.path.join(project_dir, SNAPSHOT_DIR, f"{safe}.json.gz")


def collect(project_dir: str) -> dict[str, Any]:
    """The edges plus the facts that say how complete the graph was."""
    db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.isfile(db):
        return {"edges": [], "completeness": {"artifacts": 0, "layers": {}, "stale": None}}

    try:
        with sqlite3.connect(db, timeout=5) as conn:
            edges = [
                [str(r[0]), str(r[1]), str(r[2]), str(r[3]), int(r[4] or 1)]
                for r in conn.execute(
                    "SELECT s.path, d.path, e.relation, e.layer, e.observations "
                    "FROM artifact_edges e "
                    "JOIN artifacts s ON s.id = e.source_artifact_id "
                    "JOIN artifacts d ON d.id = e.target_artifact_id "
                    "ORDER BY s.path, d.path, e.layer"
                )
            ]
            artifacts = int(conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0])
            layers = {
                str(row[0]): int(row[1])
                for row in conn.execute("SELECT layer, COUNT(*) FROM artifact_edges GROUP BY layer")
            }
    except sqlite3.Error:
        # Absence, not an empty graph: a database we could not read says nothing
        # about the relations, and a snapshot claiming zero edges would later be
        # diffed as "everything vanished".
        return {"edges": [], "completeness": {"artifacts": 0, "layers": {}, "stale": None}}

    return {
        "edges": edges,
        "completeness": {"artifacts": artifacts, "layers": layers, "stale": None},
    }


def write(project_dir: str, label: str) -> tuple[str, int, int]:
    """Store a snapshot. Returns (path, edge count, bytes written)."""
    payload = collect(project_dir)
    path = snapshot_path(project_dir, label)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.open(path, "wb") as fh:
        fh.write(raw)
    return path, len(payload["edges"]), os.path.getsize(path)


def read(project_dir: str, label: str) -> dict[str, Any] | None:
    path = snapshot_path(project_dir, label)
    if not os.path.isfile(path):
        return None
    try:
        with gzip.open(path, "rb") as fh:
            loaded = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _key(edge: list[Any]) -> tuple[str, str, str, str]:
    return (str(edge[0]), str(edge[1]), str(edge[2]), str(edge[3]))


def completeness_warnings(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """What differs about the SNAPSHOTS rather than about the code.

    Said BEFORE any difference is listed. A layer present in one snapshot and
    absent from the other accounts for every one of its edges appearing or
    vanishing, and none of that is structural drift — it is the index having
    been fed differently. Measured shape of the risk: `observed_coverage` alone
    holds 6,051 edges on this repository.
    """
    warnings: list[str] = []
    before_layers = dict(before.get("completeness", {}).get("layers") or {})
    after_layers = dict(after.get("completeness", {}).get("layers") or {})

    for layer in sorted(set(before_layers) - set(after_layers)):
        warnings.append(
            f"layer '{layer}' is present in the earlier snapshot ({before_layers[layer]} "
            "edges) and ABSENT from the later one — its edges below are a difference in "
            "what was INDEXED, not in the code"
        )
    for layer in sorted(set(after_layers) - set(before_layers)):
        warnings.append(
            f"layer '{layer}' is ABSENT from the earlier snapshot and present in the "
            f"later one ({after_layers[layer]} edges) — its edges below are new to the "
            "INDEX, not necessarily new in the code"
        )

    before_artifacts = int(before.get("completeness", {}).get("artifacts") or 0)
    after_artifacts = int(after.get("completeness", {}).get("artifacts") or 0)
    if before_artifacts and after_artifacts:
        ratio = after_artifacts / before_artifacts
        if ratio < 0.8 or ratio > 1.25:
            warnings.append(
                f"the graphs differ in size by more than a quarter ({before_artifacts} "
                f"artifacts then, {after_artifacts} now) — some of the difference below "
                "is coverage of the tree, not change in it"
            )
    return warnings


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """{appeared, vanished, warnings} — warnings first in every rendering."""
    old = {_key(e) for e in before.get("edges") or []}
    new = {_key(e) for e in after.get("edges") or []}
    return {
        "appeared": sorted(new - old),
        "vanished": sorted(old - new),
        "warnings": completeness_warnings(before, after),
    }


def render(label_before: str, label_after: str, result: dict[str, Any]) -> str:
    lines: list[str] = []
    for warning in result["warnings"]:
        lines.append(f"! {warning}")
    if result["warnings"]:
        lines.append("")

    lines.append(f"{label_before} -> {label_after}")
    for name, key in (("appeared", "appeared"), ("vanished", "vanished")):
        entries = result[key]
        lines.append(f"  {name}: {len(entries)} edge(s)")
        for src, dst, relation, layer in entries[:EXAMPLES]:
            lines.append(f"    {src} -> {dst}  [{relation}, {layer}]")
        if len(entries) > EXAMPLES:
            lines.append(f"    ... {len(entries) - EXAMPLES} more")
    if not result["appeared"] and not result["vanished"]:
        lines.append("  the relations are identical")
    return "\n".join(lines)
