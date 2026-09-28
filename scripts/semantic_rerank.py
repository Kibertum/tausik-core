"""Optional semantic re-rank ON TOP of FTS5/BM25F, with the gates the evidence demands.

WHY THIS IS A RE-RANK AND NOT A SEARCH. The plan for this feature was pure local embeddings.
The published record turned that around and the numbers are the argument:

* Cursor's online A/B (2025-11-06): embeddings won +12.5% on offline retrieval accuracy and
  +0.3% on the metric that pays -- code actually kept -- rising to +2.6% only on repositories
  past a thousand files.
* Sourcegraph REMOVED embeddings in favour of BM25F over a code graph.
* Short keyword queries, which are the dominant shape an agent sends, collapse semantic
  retrieval to nDCG@10 near zero.
* CORE-Bench (June 2026): the hybrid wins and no single method dominates.

So the keyword path stays the spine -- `bm25(fts_memory, 10.0, 1.0, 3.0)` already weights
title over tags over content, which was the cheapest win and is already taken -- and this
layer only ever REORDERS candidates the keyword path already found. It cannot introduce a row
FTS5 did not return, and it cannot remove one.

THREE GATES, EACH FROM A MEASUREMENT ABOVE. A provider has to be configured; the query has to
look like a question rather than a bag of keywords; and the corpus has to be big enough for
the effect to exist at all. Any gate closed means the caller gets the FTS5 order untouched --
not an error, not an empty list.

MEASURED ON OUR OWN TRAFFIC, because the vendor benchmarks are not trustworthy here: LoCoMo
was discredited when a no-memory baseline beat Mem0 73:68. The sidecar records the gate
decision for every search, so the honest answer to "does this help us" is a number from this
machine. On the machine where it was written the shared store held 45 rows, so the corpus gate
is CLOSED and the measured activation rate is zero. That is the finding, not a gap: the layer
exists switched off until the corpus makes it worth paying for.

NO QUERY TEXT IS EVER LOGGED. A search string can carry a secret, and a telemetry file is the
last place to learn that. The sidecar records shapes and outcomes, never the words.
"""

from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Callable, Final, NamedTuple

#: Below this many live rows the effect does not exist to be had: the online A/B found +0.3%
#: overall and +2.6% only past a thousand files. Paying a provider round-trip on a corpus
#: smaller than that buys latency and nothing else.
MIN_CORPUS_ROWS: Final[int] = 1_000

#: A natural-language query carries GLUE -- a question word, a pronoun, an auxiliary. A bag of
#: content words does not, and that is the shape semantic retrieval fails on. Both languages
#: this project is written in, because an agent asks in either.
GLUE_WORDS: Final[frozenset[str]] = frozenset(
    {
        "как",
        "почему",
        "что",
        "чем",
        "где",
        "когда",
        "зачем",
        "мы",
        "я",
        "это",
        "был",
        "было",
        "есть",
        "делать",
        "решали",
        "how",
        "why",
        "what",
        "which",
        "where",
        "when",
        "did",
        "do",
        "does",
        "we",
        "i",
        "is",
        "was",
        "were",
        "the",
        "a",
        "an",
        "to",
        "for",
        "about",
    }
)

#: Four tokens is the shortest thing that can be a question rather than a phrase. Three or
#: fewer is a keyword query however it is punctuated.
MIN_WORDS: Final[int] = 4

#: Candidates asked of FTS5 per requested hit. Four is enough room for a re-rank to move
#: something into the top of the page and small enough to embed inside the latency budget.
CANDIDATE_MULTIPLIER: Final[int] = 4

#: Reciprocal Rank Fusion's constant, as published. RRF rather than a weighted sum of scores
#: because BM25 and cosine are not on the same scale and calibrating them needs labelled data
#: this project does not have — a made-up weight would be a number with no evidence behind it.
RRF_K: Final[int] = 60

#: The whole layer's share of a search. `docs/ru/semantic-rerank.md` promises under two
#: seconds for a local search; the keyword path costs milliseconds, so this is the budget that
#: matters. Exceeding it returns the keyword order and says so in the sidecar.
DEFAULT_TIMEOUT_S: Final[float] = 2.0

SIDECAR_NAME: Final[str] = "semantic_rerank.jsonl"


class Provider(NamedTuple):
    """Where to get embeddings. Resolved from config; absent means the gate is closed."""

    endpoint: str
    model: str
    timeout_s: float


class Decision(NamedTuple):
    """Why the layer did or did not run. ``gate`` is None when it ran."""

    gate: str | None
    corpus_rows: int
    candidates: int
    changed_top: bool
    elapsed_ms: int

    @property
    def ran(self) -> bool:
        return self.gate is None


def is_natural_language(query: str) -> bool:
    """A question, not a bag of keywords.

    The distinction is the difference between the layer helping and the layer making things
    worse: short keyword queries take semantic retrieval to nDCG@10 near zero, so they belong
    to the keyword path by construction rather than by preference.
    """
    words = [w for w in "".join(c if c.isalnum() else " " for c in query.lower()).split() if w]
    if len(words) < MIN_WORDS:
        return False
    return any(w in GLUE_WORDS for w in words)


def provider_from_config(cfg: dict[str, Any] | None) -> Provider | None:
    """``semantic_rerank`` block, or None.

    DEFAULT OFF, and that is the zero-dependency promise: a checkout with no configuration
    behaves exactly as it did before this module existed, which the negative test pins.
    """
    block = (cfg or {}).get("semantic_rerank")
    if not isinstance(block, dict) or not block.get("enabled"):
        return None
    endpoint = block.get("endpoint")
    model = block.get("model")
    if not isinstance(endpoint, str) or not endpoint or not isinstance(model, str) or not model:
        return None
    try:
        timeout = float(block.get("timeout_s", DEFAULT_TIMEOUT_S))
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_S
    if endpoint_refusal(endpoint) is not None:
        return None
    return Provider(endpoint, model, max(0.1, timeout))


def endpoint_refusal(endpoint: str) -> str | None:
    """Why this endpoint may not be handed store text, or None.

    THE DECISION IS THE BOUNDARY'S, not this module's. `publication_boundary` is the one place
    that answers "may these bytes go there", and an embeddings provider receives whole rows
    verbatim -- the same unredacted free text the file-destination refusal keeps at home. A
    second opinion here is how four of them appeared before decision #358 removed them.

    Returned rather than raised: a misconfigured endpoint must close the gate, not break a
    search. `--probe` prints this so the refusal is visible instead of looking like "off".
    """
    from publication_boundary import assert_loopback_service
    from tausik_utils import ServiceError

    try:
        assert_loopback_service(endpoint)
    except ServiceError as e:
        return str(e)
    return None


def gate(query: str, corpus_rows: int, prov: Provider | None) -> str | None:
    """The reason the layer stays out of the way, or None to proceed.

    Named reasons rather than a boolean: the sidecar records which gate closed, and "we never
    switched it on" and "it was never worth switching on" are different answers to the same
    question about whether the feature earns its keep.
    """
    if prov is None:
        return "no-provider"
    if corpus_rows < MIN_CORPUS_ROWS:
        return "small-corpus"
    if not is_natural_language(query):
        return "keyword-query"
    return None


def embed(prov: Provider, texts: list[str]) -> list[list[float]] | None:
    """Batch embeddings over HTTP, or None on any failure.

    STDLIB ONLY and BATCHED. One request per candidate would put twenty round-trips inside a
    two-second budget; the batch endpoint makes it two. A provider that answers with the wrong
    shape is treated exactly like a provider that is down — the caller degrades rather than
    guessing what the numbers meant.
    """
    import urllib.error
    import urllib.request

    payload = json.dumps({"model": prov.model, "input": texts}).encode("utf-8")
    req = urllib.request.Request(
        prov.endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=prov.timeout_s) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    vectors = body.get("embeddings") if isinstance(body, dict) else None
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        return None
    out: list[list[float]] = []
    for v in vectors:
        if not isinstance(v, list) or not v or not all(isinstance(x, (int, float)) for x in v):
            return None
        out.append([float(x) for x in v])
    return out


def cosine(a: list[float], b: list[float]) -> float:
    """Zero for a zero vector rather than a division error — a degenerate embedding is a
    provider problem, and it must cost the row its boost, not the search its answer."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def fuse(keyword_order: list[int], semantic_order: list[int]) -> list[int]:
    """Reciprocal Rank Fusion of two orderings of the same index set.

    Both lists hold the same indices; only their order differs. A row absent from one list
    would silently lose its contribution, so the function requires the sets to match and falls
    back to the keyword order when they do not — a fusion that quietly drops a hit is worse
    than no fusion.
    """
    if set(keyword_order) != set(semantic_order):
        return list(keyword_order)
    score: dict[int, float] = {}
    for rank, idx in enumerate(keyword_order):
        score[idx] = score.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, idx in enumerate(semantic_order):
        score[idx] = score.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    # Ties resolve to the keyword order, which is the spine: position in the original list is
    # the second key, so an equal score never reshuffles what FTS5 decided.
    position = {idx: rank for rank, idx in enumerate(keyword_order)}
    return sorted(score, key=lambda i: (-score[i], position[i]))


def rerank(
    query: str,
    rows: list[dict[str, Any]],
    prov: Provider | None,
    corpus_rows: int,
    limit: int,
    text_of: Callable[[dict[str, Any]], str] | None = None,
    embedder: Callable[[Provider, list[str]], list[list[float]] | None] = embed,
) -> tuple[list[dict[str, Any]], Decision]:
    """``(rows, decision)`` — the FTS5 page, reordered only when every gate is open.

    ``rows`` arrives in keyword order and longer than ``limit`` (the candidate window). The
    return is always exactly the first ``limit`` of SOME ordering of those rows: this layer
    reorders, it never retrieves and never filters.
    """
    started = time.monotonic()
    closed = gate(query, corpus_rows, prov)
    if closed is not None:
        return rows[:limit], Decision(closed, corpus_rows, len(rows), False, 0)
    assert prov is not None
    as_text = text_of or (lambda r: f"{r.get('title') or ''}\n{r.get('content') or ''}")
    vectors = embedder(prov, [query] + [as_text(r) for r in rows])
    elapsed = int((time.monotonic() - started) * 1000)
    if vectors is None:
        return rows[:limit], Decision("provider-failed", corpus_rows, len(rows), False, elapsed)
    if elapsed > prov.timeout_s * 1000:
        return rows[:limit], Decision("over-budget", corpus_rows, len(rows), False, elapsed)
    q_vec, row_vecs = vectors[0], vectors[1:]
    keyword_order = list(range(len(rows)))
    semantic_order = sorted(keyword_order, key=lambda i: (-cosine(q_vec, row_vecs[i]), i))
    fused = fuse(keyword_order, semantic_order)
    changed = fused[:limit] != keyword_order[:limit]
    return (
        [rows[i] for i in fused[:limit]],
        Decision(None, corpus_rows, len(rows), changed, elapsed),
    )


def log_decision(tausik_dir: str, d: Decision) -> None:
    """Append one line. Best-effort: telemetry never breaks a search.

    The record carries SHAPES, never the query — a search string can hold a secret, and a
    telemetry file is the last place to find that out.
    """
    try:
        os.makedirs(tausik_dir, exist_ok=True)
        with open(os.path.join(tausik_dir, SIDECAR_NAME), "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "gate": d.gate,
                        "corpus_rows": d.corpus_rows,
                        "candidates": d.candidates,
                        "changed_top": d.changed_top,
                        "elapsed_ms": d.elapsed_ms,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except OSError:
        return


def report(tausik_dir: str) -> dict[str, Any]:
    """What the layer actually did on THIS machine's traffic.

    Absence is reported as absence: a store with no records answers ``searches: 0`` rather
    than a rate computed over nothing.
    """
    path = os.path.join(tausik_dir, SIDECAR_NAME)
    if not os.path.isfile(path):
        return {"searches": 0, "ran": 0, "changed_top": 0, "gates": {}, "p95_ms": None}
    gates: dict[str, int] = {}
    ran = changed = 0
    took: list[int] = []
    total = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # a truncated tail line is not a reason to refuse the report
            total += 1
            g = rec.get("gate")
            if g is None:
                ran += 1
                took.append(int(rec.get("elapsed_ms") or 0))
                if rec.get("changed_top"):
                    changed += 1
            else:
                gates[str(g)] = gates.get(str(g), 0) + 1
    p95 = None
    if took:
        took.sort()
        p95 = took[min(len(took) - 1, int(len(took) * 0.95))]
    return {"searches": total, "ran": ran, "changed_top": changed, "gates": gates, "p95_ms": p95}


def render_report(r: dict[str, Any]) -> str:
    if not r["searches"]:
        return (
            "Semantic re-rank: no searches recorded. Nothing ran and nothing was measured — "
            "which is the honest answer, not a zero rate."
        )
    lines = [
        f"Semantic re-rank over {r['searches']} search(es): ran {r['ran']}, "
        f"changed the top page {r['changed_top']} time(s)."
    ]
    if r["p95_ms"] is not None:
        lines.append(f"  p95 latency of the layer: {r['p95_ms']} ms (budget {DEFAULT_TIMEOUT_S}s)")
    for g, n in sorted(r["gates"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  gate {g}: {n}")
    return "\n".join(lines)


def probe() -> str:
    """What the gates say about THIS machine, read from the live store rather than a log.

    The sidecar only fills once a provider is configured, and instrumenting the switched-off
    path would put a file write on every search to learn a fact the corpus already states. So
    the on-our-own-traffic answer for a checkout with no provider comes from here: the corpus
    size against the threshold, and the gate each query shape would meet.
    """
    import sqlite3

    try:
        from knowledge_db import knowledge_db_exists, knowledge_db_path
        from project_config import load_config
    except ImportError as e:  # pragma: no cover - only outside the project tree
        return f"cannot probe: {e}"
    prov = provider_from_config(load_config())
    rows = 0
    if knowledge_db_exists():
        conn = sqlite3.connect(knowledge_db_path())
        try:
            rows = int(
                conn.execute("SELECT COUNT(*) FROM memory WHERE archived_at IS NULL").fetchone()[0]
            )
        except sqlite3.Error:
            rows = 0
        finally:
            conn.close()
    share = 100.0 * rows / MIN_CORPUS_ROWS
    lines = [
        f"Shared store: {rows} live row(s) against a threshold of {MIN_CORPUS_ROWS} "
        f"({share:.1f}% of it).",
        f"Provider configured: {'yes' if prov else 'no'}.",
    ]
    block = (load_config() or {}).get("semantic_rerank")
    if prov is None and isinstance(block, dict) and block.get("enabled"):
        refusal = endpoint_refusal(str(block.get("endpoint") or ""))
        if refusal:
            lines.append(f"  endpoint REFUSED: {refusal}")
    for shape, q in (
        ("natural-language", "как мы это решали в прошлый раз"),
        ("keyword", "fts5 bm25 weights"),
    ):
        reason = gate(q, rows, prov)
        lines.append(f"  a {shape} query would meet: {reason or 'no gate — the layer runs'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Semantic re-rank: gates and measured effect")
    p.add_argument("--report", action="store_true", help="What the layer did on this traffic")
    p.add_argument("--tausik-dir", default=os.path.join(".tausik"))
    p.add_argument("--explain", metavar="QUERY", help="Say which gate a query would meet")
    p.add_argument("--probe", action="store_true", help="What the gates say about this machine")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.explain:
        shape = "natural-language" if is_natural_language(args.explain) else "keyword"
        print(f"query shape: {shape} (min {MIN_WORDS} words and one glue word)")
    if args.probe:
        print(probe())
    if args.report or not (args.explain or args.probe):
        print(render_report(report(args.tausik_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
