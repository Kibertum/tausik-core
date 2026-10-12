"""Reproducible retrieval measurement for the codebase-RAG index.

Answers one question with one number: for a fixed set of queries, how often
does the chunk that should be found appear in the top K results. Run it with
the context header on and off to get the before/after pair that
`rag-contextual-chunk-prefix` requires.

Two query sets, because a single one cannot catch both failure directions:

  * ``context`` — the case the header exists for. The query names what the FILE
    is about plus an identifier that lives in a chunk somewhere inside it. A
    chunk cut out of the middle of that file has no words describing the file,
    so without a header it can only be reached through the identifier.
  * ``control`` — queries built ONLY from words already inside the target
    chunk. The header must not help here, and above all must not HURT: adding
    text to the index dilutes term frequency, and a change that improves the
    first set while damaging this one is not an improvement.

Queries are derived mechanically from the corpus, not hand-written, so the set
cannot be quietly tuned toward a flattering result. Sampling is deterministic
(fixed stride, no RNG), so two runs over the same tree ask the same questions.

Usage:
    python scripts/rag_retrieval_bench.py [--limit 10] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from typing import Any

_RAG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "harness", "claude", "mcp", "codebase-rag"
)
sys.path.insert(0, os.path.abspath(_RAG_DIR))

import rag_context  # noqa: E402
from rag_indexer import annotate_chunks, chunk_file  # noqa: E402
from rag_store import RAGStore  # noqa: E402

CORPUS_DIRS = ("scripts", "bootstrap")
SAMPLE_STRIDE = 2  # deterministic sampling; no RNG, so the set is stable
MIN_IDENT_LEN = 6
_IDENT_RE = re.compile(r"\b([a-z][a-z0-9]{2,}(?:_[a-z0-9]+)+)\b")


def _corpus(repo_root: str) -> list[tuple[str, str]]:
    """(rel_path, content) for every Python file in the corpus dirs, sorted."""
    out: list[tuple[str, str]] = []
    for base in CORPUS_DIRS:
        root = os.path.join(repo_root, base)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, repo_root).replace(os.sep, "/")
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        out.append((rel, fh.read()))
                except OSError:
                    continue
    return sorted(out)


def build_index(db_path: str, corpus: list[tuple[str, str]], *, with_prefix: bool) -> RAGStore:
    store = RAGStore(db_path)
    for rel, content in corpus:
        chunks = chunk_file(content, "python")
        if not chunks:
            continue
        annotate_chunks(chunks, rel, "python", content)
        if not with_prefix:
            for chunk in chunks:
                chunk["context_prefix"] = ""
        store.upsert_file(rel, chunks)
    return store


def _identifier(text: str) -> str:
    """A distinctive multi-word identifier from the text, or ""."""
    for match in _IDENT_RE.finditer(text):
        token = match.group(1)
        if len(token) >= MIN_IDENT_LEN:
            return token
    return ""


def build_queries(corpus: list[tuple[str, str]]) -> dict[str, list[dict[str, Any]]]:
    """Derive both query sets from the corpus. Deterministic."""
    context_q: list[dict[str, Any]] = []
    control_q: list[dict[str, Any]] = []
    for i, (rel, content) in enumerate(corpus):
        if i % SAMPLE_STRIDE:
            continue
        chunks = chunk_file(content, "python")
        if len(chunks) < 3:
            continue  # need a genuine "middle of the file" chunk
        summary = rag_context.extract_module_summary(content)
        if not summary:
            continue
        target = chunks[len(chunks) // 2]
        ident = _identifier(target["content"])
        if not ident:
            continue
        summary_words = [w for w in re.split(r"[^A-Za-z0-9]+", summary) if len(w) > 3][:4]
        if len(summary_words) < 2:
            continue
        context_q.append(
            {
                "query": " ".join(summary_words) + " " + ident.replace("_", " "),
                "file": rel,
                "start_line": target.get("start_line"),
            }
        )
        control_q.append(
            {
                "query": ident.replace("_", " "),
                "file": rel,
                "start_line": target.get("start_line"),
            }
        )
    return {"context": context_q, "control": control_q}


def recall_at_k(store: RAGStore, queries: list[dict[str, Any]], k: int) -> dict[str, Any]:
    """Fraction of queries whose TARGET CHUNK is in the top K.

    Chunk-level, not file-level: with 350 files and K=10 a file-level hit is
    almost free, and a metric already at 1.0 cannot show an improvement or a
    regression. What matters to a reader is whether the right passage came
    back, so a hit requires the returned chunk's line range to contain the
    target's first line.
    """
    hits = 0
    for q in queries:
        results = store.search(q["query"], limit=k)
        for r in results:
            if r["file_path"] != q["file"]:
                continue
            start, end = r.get("start_line"), r.get("end_line")
            if start is None or end is None or q["start_line"] is None:
                hits += 1
                break
            if start <= q["start_line"] <= end:
                hits += 1
                break
    total = len(queries)
    return {"hits": hits, "total": total, "recall": round(hits / total, 4) if total else 0.0}


def run(repo_root: str, k: int) -> dict[str, Any]:
    corpus = _corpus(repo_root)
    queries = build_queries(corpus)
    report: dict[str, Any] = {
        "corpus_files": len(corpus),
        "k": k,
        "queries": {name: len(qs) for name, qs in queries.items()},
        "sets": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        for label, with_prefix in (("baseline", False), ("with_prefix", True)):
            store = build_index(os.path.join(tmp, f"{label}.db"), corpus, with_prefix=with_prefix)
            try:
                for name, qs in queries.items():
                    report["sets"].setdefault(name, {})[label] = recall_at_k(store, qs, k)
            finally:
                store.close()
    for name, arm in report["sets"].items():
        arm["delta"] = round(arm["with_prefix"]["recall"] - arm["baseline"]["recall"], 4)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10, help="top-K considered a hit")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report = run(repo_root, args.limit)

    if args.as_json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"corpus: {report['corpus_files']} files   K={report['k']}")
    for name, arm in report["sets"].items():
        n = report["queries"][name]
        base, new = arm["baseline"], arm["with_prefix"]
        print(
            f"  {name:8} n={n:4}  baseline recall@{report['k']}={base['recall']:.4f}"
            f"  with_prefix={new['recall']:.4f}  delta={arm['delta']:+.4f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
