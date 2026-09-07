"""Building the artifact graph, and answering from it HONESTLY.

Two layers are built here, and they are kept apart on purpose:

  * LAYER 0 -- co-change, read from git history. Needs no parser, so it works
    for documentation, configuration and images exactly as well as for code.
    Its confidence is DERIVED from how often two files appeared together, never
    assigned as a constant: an edge seen once and an edge seen twelve times are
    different claims and must not print the same number.
  * LAYER 1 -- declarations the repository ALREADY makes. `CROSSCUTTING_SCOPE`
    in a test, `relevant_files` and `scope_paths` on a task. These are read, not
    requested again: asking an author to re-declare what they already declared
    is how a second registry starts drifting from the first.

THE QUERY IS THE POINT, NOT THE STORE. `neighbours_of` recomputes each involved
artifact's fingerprint from disk and marks the answer partially stale, naming
the artifacts it no longer describes. A silent answer over stale rows is the
worst possible outcome, because it is indistinguishable from a correct one --
which is why the staleness flag is computed on every query rather than at index
time.

NAMED LIMITATION -- HUB FILES. `CHANGELOG.md` and the two READMEs appear in
almost every task's `relevant_files`, so they collect a declared edge to almost
everything. Those edges are TRUE: someone really did declare them together.
They are also nearly uninformative, and ranking by confidence puts them first,
because a declaration's confidence measures whether it was made, not how much
it narrows anything down. Measured on this repository: 23,358 declared edges,
of which the busiest module's top neighbours are all changelog and readme.
Down-weighting a hub is a RANKING decision belonging to whoever asks the
question -- the substrate's job is to store the claim and its provenance
without pretending it is more specific than it is. Said here rather than left
for a reader to discover, because an unnamed limitation is how a graph starts
being trusted for something it cannot do.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Any

from verify_files_hash import compute_files_hash

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

#: Extensions that decide an artifact's kind. Deliberately coarse: the kind is
#: for grouping answers, not for dispatch, and a wrong guess costs a label.
_KIND_BY_SUFFIX = {
    ".py": "code",
    ".md": "doc",
    ".rst": "doc",
    ".yml": "config",
    ".yaml": "config",
    ".json": "config",
    ".toml": "config",
    ".cfg": "config",
    ".ini": "config",
}

#: A GROUPING larger than this says nothing per pair, so it produces no edges.
#: Applies to both layers, because both build pairs out of a set: a sweeping
#: rename puts hundreds of unrelated files in one commit, and a large task
#: declares dozens of `relevant_files` that are related to the TASK and not to
#: each other. MEASURED before the cap was applied to layer 1: pairing every
#: declared file produced 65,318 edges -- `CHANGELOG.md` "references"
#: `.gitattributes` because one task touched both. Noise at that volume does
#: not dilute the signal, it replaces it.
_MAX_FILES_PER_GROUP = 25


def classify(path: str) -> str:
    """The artifact kind for a repo-relative path."""
    base = os.path.basename(path)
    if base.startswith("test_") or path.replace("\\", "/").startswith("tests/"):
        return "test"
    return _KIND_BY_SUFFIX.get(os.path.splitext(path)[1].lower(), "other")


def fingerprint(path: str, root: str) -> str:
    """The per-file fingerprint staleness is measured against.

    One path, through `compute_files_hash`, so this is not a second answer to
    "did this file change" -- that function already hashes canonical path,
    mtime_ns, size and a content head, and carries the measurements behind
    those choices. A missing file hashes to its own stable sentinel there, so a
    deleted artifact reads as changed rather than raising.
    """
    return compute_files_hash([path], root=root)


class ArtifactGraphMixin:
    """Index the repository into the graph, and answer from it with freshness."""

    be: SQLiteBackend

    # --- indexing ---

    def graph_index_paths(self, paths: list[str], root: str = ".") -> int:
        """Record artifacts at their current fingerprint. Returns how many."""
        n = 0
        for path in paths:
            rel = path.replace("\\", "/")
            self.be.artifact_upsert(rel, classify(rel), fingerprint(rel, root))
            n += 1
        return n

    def graph_stale_artifacts(self, root: str = ".") -> list[dict[str, Any]]:
        """Artifacts whose file on disk no longer matches what was indexed.

        Computed by comparison, never by a global timestamp: the answer has to
        be "these ten of a hundred", not "the graph is old".
        """
        stale: list[dict[str, Any]] = []
        for row in self.be.artifact_list():
            if fingerprint(row["path"], root) != row["content_hash"]:
                stale.append({"path": row["path"], "indexed_at": row["indexed_at"]})
        return stale

    # --- layer 0: co-change, from git ---

    def graph_build_cochange(
        self, root: str = ".", *, window: int = 200, min_shared: int = 2
    ) -> int:
        """Edges between files that keep appearing in the same commit.

        `min_shared` exists because a single shared commit is not evidence of
        anything -- two files edited together once may never be related again.
        Confidence rises with the count and is capped below 1.0: co-change is
        an OBSERVATION, and no number of observations turns it into the
        certainty a declaration carries.
        """
        commits = _commit_file_sets(root, window)
        pair_counts: dict[tuple[str, str], int] = {}
        for files in commits:
            if len(files) > _MAX_FILES_PER_GROUP:
                continue
            ordered = sorted(files)
            for i, a in enumerate(ordered):
                for b in ordered[i + 1 :]:
                    pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1

        written = 0
        for (a, b), count in pair_counts.items():
            if count < min_shared:
                continue
            if not (
                os.path.exists(os.path.join(root, a)) and os.path.exists(os.path.join(root, b))
            ):
                continue
            src = self.be.artifact_upsert(a, classify(a), fingerprint(a, root))
            dst = self.be.artifact_upsert(b, classify(b), fingerprint(b, root))
            # Saturating, never reaching 1.0 — see the docstring.
            confidence = min(0.9, count / (count + 3.0))
            self.be.artifact_edge_add(
                src, dst, "co_changes", "git_cochange", confidence, observations=count
            )
            written += 1
        return written

    # --- layer 1: declarations the repository already makes ---

    def graph_build_declared(self, root: str = ".") -> int:
        """Read edges out of declarations that already exist in the tree/DB.

        Confidence is 1.0 and that is not a shortcut: a declaration is somebody
        stating the relation, so the graph is not guessing. The LAYER is what
        keeps that separable from an inference of the same shape.
        """
        written = 0
        written += self._declared_from_crosscutting(root)
        written += self._declared_from_tasks(root)
        return written

    def _declared_from_crosscutting(self, root: str) -> int:
        """`CROSSCUTTING_SCOPE = [...]` in a test names what that test guards."""
        import ast

        tests_dir = os.path.join(root, "tests")
        if not os.path.isdir(tests_dir):
            return 0
        written = 0
        for name in sorted(os.listdir(tests_dir)):
            if not (name.startswith("test_") and name.endswith(".py")):
                continue
            rel = f"tests/{name}"
            try:
                tree = ast.parse(open(os.path.join(root, rel), encoding="utf-8").read())
            except (OSError, SyntaxError):
                continue
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                if not any(
                    isinstance(t, ast.Name) and t.id == "CROSSCUTTING_SCOPE" for t in node.targets
                ):
                    continue
                if not isinstance(node.value, ast.List):
                    continue
                src = self.be.artifact_upsert(rel, classify(rel), fingerprint(rel, root))
                for elt in node.value.elts:
                    if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                        continue
                    written += self._edge_to_declared_path(
                        src, elt.value, root, "declared_crosscutting", "covers", rel
                    )
        return written

    def _declared_from_tasks(self, root: str) -> int:
        """Files an author grouped under one task — already recorded, never asked for twice.

        THE RELATION IS `co_changes`, NOT `references`. What a task's
        `relevant_files` states is "these were worked on together"; it says
        nothing about one file mentioning another. Calling that `references`
        would put a claim in the graph that nobody made — the same invented
        fact this table exists to refuse. The LAYER is what separates this
        declared grouping from the one git infers.

        `_MAX_FILES_PER_GROUP` applies here for the reason it applies to
        commits, and the measurement that put it here is in its comment: a
        large task relates its files to the TASK, not to each other, and
        pairing them anyway produced 65,318 edges of pure noise.
        """
        written = 0
        for task in self.be.task_list(limit=100000):
            slug = task.get("slug")
            for field, layer in (
                ("relevant_files", "declared_relevant_files"),
                ("scope_paths", "declared_scope_paths"),
            ):
                declared = [str(p).replace("\\", "/") for p in _json_list(task.get(field))]
                present = [p for p in declared if os.path.isfile(os.path.join(root, p))]
                if len(present) < 2 or len(present) > _MAX_FILES_PER_GROUP:
                    continue
                ordered = sorted(set(present))
                for i, a in enumerate(ordered):
                    src = self.be.artifact_upsert(a, classify(a), fingerprint(a, root))
                    for b in ordered[i + 1 :]:
                        written += self._edge_to_declared_path(
                            src, b, root, layer, "co_changes", f"task:{slug}"
                        )
        return written

    def _edge_to_declared_path(
        self, src: int, target: str, root: str, layer: str, relation: str, source_ref: str
    ) -> int:
        """One declared edge, or 0 when the target is not a file we can point at.

        A declaration may name a DIRECTORY prefix (`.github/workflows/`). Those
        are skipped rather than expanded: an edge to a directory would claim a
        relation to files nobody named, which is precisely the invented fact
        this table refuses to store.
        """
        rel = target.replace("\\", "/")
        if not os.path.isfile(os.path.join(root, rel)):
            return 0
        dst = self.be.artifact_upsert(rel, classify(rel), fingerprint(rel, root))
        if dst == src:
            return 0
        self.be.artifact_edge_add(src, dst, relation, layer, 1.0, source_ref=source_ref)
        return 1

    # --- the query ---

    def neighbours_of(self, path: str, root: str = ".") -> dict[str, Any]:
        """What the graph says about `path`, WITH what it can no longer vouch for.

        Every artifact in the answer — the subject and each neighbour — has its
        fingerprint recomputed from disk. If any of them has moved on, the
        answer is flagged and the offenders are named. It would be cheaper to
        trust the stored hashes; it would also make a stale answer look exactly
        like a fresh one, and that is the one outcome this graph must never
        produce.
        """
        rel = path.replace("\\", "/")
        subject = self.be.artifact_get(rel)
        if not subject:
            return {"path": rel, "known": False, "stale": [], "partially_stale": False, "edges": []}

        stale: list[str] = []
        if fingerprint(rel, root) != subject["content_hash"]:
            stale.append(rel)

        # Both directions: storage puts a co-change edge on one side only,
        # and a caller asking what relates to a file means either side.
        edges = self.be.edges_touching_artifact(int(subject["id"]))
        for edge in edges:
            target = str(edge["target_path"])
            if fingerprint(target, root) != edge["target_hash"] and target not in stale:
                stale.append(target)

        return {
            "path": rel,
            "known": True,
            "indexed_at": subject["indexed_at"],
            "partially_stale": bool(stale),
            "stale": sorted(stale),
            "edges": [
                {
                    "target": e["target_path"],
                    "direction": e["direction"],
                    "relation": e["relation"],
                    "layer": e["layer"],
                    "confidence": e["confidence"],
                    "observations": e["observations"],
                    "source_ref": e["source_ref"],
                }
                for e in edges
            ],
        }


def _json_list(raw: Any) -> list[Any]:
    import json

    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _commit_file_sets(root: str, window: int) -> list[list[str]]:
    """File lists of the last `window` commits, or [] outside a git tree.

    Returns [] rather than raising when git is absent or this is not a
    repository: layer 0 is one source among several, and its absence must
    degrade the graph, not break indexing.
    """
    try:
        proc = subprocess.run(
            ["git", "log", f"-{window}", "--name-only", "--pretty=format:%H", "--no-merges"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            # This module is reachable from the MCP server, where nothing is
            # attached to feed a prompt: a subprocess left with an inherited
            # stdin can block forever instead of failing. DEVNULL makes that a
            # refusal rather than a hang.
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    commits: list[list[str]] = []
    current: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            if current:
                commits.append(current)
            current = []
            continue
        current.append(line.replace("\\", "/"))
    if current:
        commits.append(current)
    return commits
