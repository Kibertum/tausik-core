"""Artifact graph -- code and documentation as entities in the SAME database.

Tasks, decisions, memory and SPECs are already entities with edges
(`memory_edges`). Two kinds were missing: CODE and DOCUMENTATION. This extends
that graph rather than starting a second one, which is the condition the work
was accepted under -- absorb, do not stand alongside.

PROVENANCE IS NOT AN OPTIONAL COLUMN. "co-changed in 12 commits" and "declared
in relevant_files" are DIFFERENT claims, and a graph that cannot tell them apart
turns a guess into a fact -- the disease this release has been treating
everywhere else. So `layer` is NOT NULL with a closed list, and `confidence` is
NOT NULL: an edge that cannot say how it was obtained cannot be written at all.
That is enforced by the schema, not by the caller remembering.

FRESHNESS IS PER ARTIFACT, NEVER GLOBAL. A graph that is 90% fresh is useful if
it says WHICH 10% is not; a graph with one global timestamp is useless from the
first edit after indexing. Each artifact carries the fingerprint it was indexed
at, and staleness is decided by recomputing that fingerprint from disk.

The fingerprint comes from `verify_files_hash.compute_files_hash`, called with
one path. It is deliberately NOT a second way to answer "did this file change":
that function already hashes (canonical path, mtime_ns, size, content head) and
carries the measurements and the security caveat behind that choice.
"""

from __future__ import annotations

# Closed lists live here rather than in the CHECK text alone so Python callers
# and the schema cannot drift apart -- the CHECK is generated FROM these.
ARTIFACT_KINDS = ("code", "doc", "test", "config", "data", "other")

#: What one artifact asserts about another.
EDGE_RELATIONS = (
    "co_changes",  # observed together in history -- says nothing about why
    "covers",  # test -> code
    "documents",  # doc -> code/symbol
    "references",  # mentions by name
    "defines",  # artifact -> symbol it declares
    "implements",  # code -> requirement
)

#: HOW an edge was obtained. The whole point of the graph carrying provenance:
#: an inference and a declaration must never be summarised into one number.
EDGE_LAYERS = (
    "git_cochange",  # layer 0: inferred from commit history
    "declared_crosscutting",  # layer 1: CROSSCUTTING_SCOPE in a test
    "declared_relevant_files",  # layer 1: a task's relevant_files
    "declared_scope_paths",  # layer 1: a task's scope_paths ACL
    "declared_renar",  # layer 1: an existing RENAR link
    # layer 2 (v59): what a test RUN actually reached. Not an inference from
    # history and not somebody's statement — a record of what happened, and the
    # strongest evidence this graph can hold about a test and a file.
    "observed_coverage",
)


def _in_list(column: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"CHECK({column} IN ({joined}))"


GRAPH_STATEMENTS: list[str] = [
    f"""CREATE TABLE IF NOT EXISTS artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL {_in_list("kind", ARTIFACT_KINDS)},
        content_hash TEXT NOT NULL,
        indexed_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind)",
    """CREATE TABLE IF NOT EXISTS artifact_symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        line INTEGER,
        UNIQUE(artifact_id, name)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_artifact_symbols_name ON artifact_symbols(name)",
    # `layer` and `confidence` are NOT NULL on purpose -- see the module
    # docstring. UNIQUE spans the layer too, so the SAME pair may legitimately
    # carry both an inferred and a declared edge: they are different claims and
    # collapsing them would destroy exactly the distinction this table exists
    # to keep.
    f"""CREATE TABLE IF NOT EXISTS artifact_edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
        target_artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
        relation TEXT NOT NULL {_in_list("relation", EDGE_RELATIONS)},
        layer TEXT NOT NULL {_in_list("layer", EDGE_LAYERS)},
        confidence REAL NOT NULL,
        observations INTEGER NOT NULL DEFAULT 1,
        source_ref TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(source_artifact_id, target_artifact_id, relation, layer)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_source ON artifact_edges(source_artifact_id)",
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_target ON artifact_edges(target_artifact_id)",
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_layer ON artifact_edges(layer)",
]

GRAPH_SQL = ";\n".join(GRAPH_STATEMENTS) + ";\n"
