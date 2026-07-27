#!/usr/bin/env python3
"""Baseline retrieval eval for the flat memory store (km-retrieval-baseline-eval).

Step 1 of 6 in the knowledge-layer rework (decision #143). No public evidence
shows that consolidating memory into topics improves answer quality; the rework's
real justification is command-merge and smaller injected context, not accuracy.
But to know in six months whether it got WORSE, we need a number NOW, against the
present baseline: FTS5 search over the flat memory entries.

This prints ONE accuracy number over a committed, CONTENT-KEYED question set. For
each question we run the same FTS search an agent would — the 2-3 distinctive
tokens someone recalling the concept would type — take the top-K results, and
count a hit when any expected content marker appears in them. The questions are
keyed on CONTENT (distinctive phrases), never on record ids, so the number
survives a reindex or an id change (the whole point of a durable baseline).

NOTE on the FTS the agent actually uses (backend_queries._sanitize_fts5): bare
tokens are implicit-AND and there is NO stemming, so the query tokens must be the
distinctive terms genuinely present in the target entry — a verbose sentence or a
wrong inflection retrieves nothing. That is a real property of the baseline, not
a flaw of this harness: it measures whether a reasonable search surfaces the entry.

Fail-safe (AC4): an empty store or an unreadable DB yields 0.0 accuracy with an
explicit note rather than a crash; a single malformed query counts as a miss.

Run:  python scripts/eval_memory_retrieval.py [--db PATH] [--top-k N] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

TOP_K_DEFAULT = 5

# Committed question set: (question, fts_query, [expected content markers]).
# A hit = any marker (case-insensitive substring) appears in the title+content of
# any top-K result. Queries use distinctive tokens present in the target entry.
QUESTIONS: list[tuple[str, str, list[str]]] = [
    # --- conventions ---
    (
        "How should a drift gate treat declared intent vs measured value?",
        "DECLARED DERIVED measurement",
        ["exact-pin", "lower-bound"],
    ),
    (
        "After editing source, what runs before task done?",
        "bootstrap ide task_done",
        ["--ide all", "зеркал"],
    ),
    ("When is a doc counter caught by the scanner?", "scan-target дрейф", ["scan-target"]),
    ("Does the doc-drift count scanner read fenced blocks?", "fenced сканер", ["fenced"]),
    ("What must accompany a borrowed idea in the CHANGELOG?", "CHANGELOG атрибуцией", ["атрибуц"]),
    (
        "A scope-narrowing check must print what by its verdict?",
        "знаменатель вердикт",
        ["знаменатель"],
    ),
    (
        "Supervision can be leaky along what dimension, invisible to tests?",
        "надзор КАНАЛУ",
        ["канал"],
    ),
    (
        "A gate over text the audited party writes must require what?",
        "факт формулировку",
        ["формулировк"],
    ),
    (
        "An instruction-message is code: what must every promised path do?",
        "обещанный путь существовать",
        ["обещанный путь", "существовать"],
    ),
    ("An external numeric fact must carry what?", "числовой факт источник", ["источник и дату"]),
    (
        "A gate shipped into other projects splits into what two parts?",
        "механизм общий конфиге",
        ["механизм общий", "политика в конфиге"],
    ),
    (
        "Adversarial review should run on what besides the original impl?",
        "Adversarial фиксы",
        ["на фиксы"],
    ),
    (
        "A shared query function narrowed — who does that change affect?",
        "Сужение функции потребителя",
        ["потребител"],
    ),
    (
        "A framework deny-list derives exceptions for its own artifacts how?",
        "Deny-list артефактов реестра",
        ["реестр"],
    ),
    # --- patterns ---
    (
        "How is MCP tool-surface scoping designed re failure mode?",
        "MCP scoping fail-open",
        ["fail-open", "safe-core"],
    ),
    (
        "Durable vs runtime state is split by what, not by gitignore?",
        "durable runtime каталога",
        ["имени каталога", "vs .tausik"],
    ),
    ("How is a trust signal from a checker carried safely?", "доверия сентинел", ["сентинел"]),
    (
        "How do you lock a known-but-unfixed hole so a fix announces itself?",
        "Тест-пин дыры",
        ["закреплен", "дыр"],
    ),
    (
        "Schema parity needs which two distinct comparisons?",
        "паритет схемы мигрированная",
        ["фикстура", "мигрирован"],
    ),
    (
        "A gate ensuring an edit reached the executable copy does what?",
        "доезд исполняемой копии",
        ["исполняемой копии"],
    ),
    (
        "A project operation must resolve paths from what, not cwd?",
        "резолвить handle cwd",
        ["переданного handle"],
    ),
    (
        "A mass edit is proven safe by what evidence?",
        "координатам AST строк",
        ["AST", "числом строк"],
    ),
    ("Retry should be applied only to what?", "Повтор класса отказ", ["честный отказ"]),
    (
        "Detectors that read prose should do what instead of crashing?",
        "Detectors degrade findings",
        ["degrade", "findings"],
    ),
    ("What is model routing computed from?", "Model routing capability-rank", ["capability-rank"]),
    (
        "Enabling a new ruff lint over many legacy sites uses what strategy?",
        "ruff lint annotate-then-flip",
        ["annotate-then-flip"],
    ),
    (
        "Derived file-export views must be free of what to keep --check stable?",
        "export views date-free",
        ["date-free"],
    ),
    # --- gotchas ---
    (
        "Deciding if an ACL is declared must read what, not the parsed list?",
        "scope ACL parse_task_acl",
        ["raw column", "raw"],
    ),
    (
        "What must you NOT run in parallel with a full-suite pytest?",
        "bootstrap full-suite pytest",
        ["bootstrap", "full-suite"],
    ),
    (
        "A full pytest concurrent with the CLI produces what false error?",
        "config-mutation teardown",
        ["config-mutation", "teardown"],
    ),
    (
        "MCP can report 'modules in sync' yet run what?",
        "modules in sync устаревший",
        ["устаревш", "sync"],
    ),
    (
        "A signed green verify coexists with a broken suite because pytest is scoped to what?",
        "verify pytest relevant_files",
        ["relevant_files"],
    ),
    (
        "PowerShell Get-Content without which flag corrupts a UTF-8 file?",
        "PowerShell Get-Content utf8",
        ["utf8", "BOM"],
    ),
    (
        "Running bootstrap --ide all mid-session does what to the MCP server?",
        "bootstrap отравляет MCP",
        ["отравляет", "MCP"],
    ),
    (
        "verify --task skips scoped gates until what is persisted?",
        "verify scoped relevant_files",
        ["relevant_files"],
    ),
    (
        "A fire-and-forget INSERT on a foreign sqlite connection leaves what?",
        "INSERT sqlite транзакцию",
        ["BEGIN IMMEDIATE", "транзакц"],
    ),
    (
        "A DB->files->DB round-trip import has which two traps?",
        "round-trip самоссылочный дубли",
        ["самоссылочн", "мультимножеств"],
    ),
    (
        "Worktree-isolated agents branch from what, not current HEAD?",
        "Worktree stale HEAD",
        ["STALE", "HEAD"],
    ),
    (
        "A slow test set reads as what, and why did three sessions miss it?",
        "медленный зависший таймаут",
        ["зависш", "таймаут"],
    ),
    # --- context ---
    (
        "What did session #145 reveal about the filesize gate?",
        "filesize gate 400",
        ["filesize", "400"],
    ),
    (
        "Does risk_score predict task escapes?",
        "risk_score побеги verified",
        ["risk_score", "побег"],
    ),
    (
        "Who is TAUSIK designed to protect against — a liar or a sincere agent?",
        "TAUSIK ИСКРЕННЕГО лжеца",
        ["ИСКРЕННЕГО", "лжеца"],
    ),
    ("There are two IDE registries — which two?", "IDE_DIRS ide_utils", ["IDE_DIRS", "ide_utils"]),
    (
        "What is the state of the MCP 2026 spec — what got deprecated?",
        "Спека MCP депрекировано",
        ["депрекирован"],
    ),
    # --- dead ends ---
    (
        "Can you chain push-ok && git push atomically in one Bash call?",
        "push-ok git push",
        ["push-ok"],
    ),
    (
        "Can you use an aliased FTS5 table in a MATCH clause?",
        "FTS5 alias MATCH",
        ["MATCH", "alias"],
    ),
    (
        "Was hash-chain computed at event insert-time?",
        "hash-chain events insert-time",
        ["hash-chain", "insert-time"],
    ),
    (
        "Does brain init create the 4 BRAIN DBs unconditionally?",
        "brain init BRAIN DBs",
        ["brain init", "4 BRAIN"],
    ),
    ("Was ChromaDB adopted for RAG?", "ChromaDB RAG", ["ChromaDB", "RAG"]),
]


def _hit(results: list[dict[str, Any]], markers: list[str], top_k: int) -> bool:
    """A hit iff a marker appears at a TOKEN START in the top-K results.

    Anchoring to a word boundary on the LEFT (not both sides) rejects a spurious
    substring match — e.g. '400' inside '24000' — while still allowing a marker to
    be a prefix of an inflected word (Russian markers like 'закреплен' matching
    'закрепление'), which whole-word matching would wrongly reject.
    """
    hay = " ".join(f"{r.get('title', '')} {r.get('content', '')}" for r in results[:top_k]).lower()
    return any(re.search(r"(?<!\w)" + re.escape(m.lower()), hay) for m in markers)


def evaluate(
    be: Any,
    top_k: int = TOP_K_DEFAULT,
    questions: list[tuple[str, str, list[str]]] | None = None,
) -> dict[str, Any]:
    """Run a question set against a memory backend (default: committed QUESTIONS).

    Returns {accuracy, hits, total, details}. Never raises: a per-question search
    error is recorded as a miss, so one bad query cannot abort the run.
    """
    qs = questions if questions is not None else QUESTIONS
    details = []
    hits = 0
    for question, query, markers in qs:
        try:
            results = be.memory_search(query, n=max(top_k, 1))
        except Exception:  # noqa: BLE001 — a malformed query is a miss, not a crash (AC4)
            results = []
        ok = _hit(results, markers, top_k)
        hits += 1 if ok else 0
        details.append({"q": question, "hit": ok, "n_results": len(results)})
    total = len(qs)
    accuracy = hits / total if total else 0.0
    return {"accuracy": accuracy, "hits": hits, "total": total, "details": details}


def _open_backend(db_path: str) -> Any:
    # SQLiteBackend AUTO-CREATES a fresh schema-initialised store for a missing
    # path, which would silently turn a typo'd --db into a spurious 0.0 run
    # against an empty DB. This is a read-only eval, so a missing file is an
    # error, not a store to create — check first (AC4 fail-safe).
    if not os.path.isfile(db_path):
        raise FileNotFoundError(db_path)
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from project_backend import SQLiteBackend

    return SQLiteBackend(db_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Baseline memory retrieval eval")
    parser.add_argument(
        "--db", default=os.path.join(".tausik", "tausik.db"), help="Path to tausik.db"
    )
    parser.add_argument("--top-k", type=int, default=TOP_K_DEFAULT, dest="top_k")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args(argv)

    try:
        be = _open_backend(args.db)
    except Exception as e:  # noqa: BLE001 — unreadable DB → 0.0, not a crash (AC4)
        print(f"memory retrieval baseline: 0.0% (DB unavailable: {e})")
        return 0

    report = evaluate(be, top_k=args.top_k)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(
        f"Memory retrieval baseline: {report['accuracy']:.1%} "
        f"({report['hits']}/{report['total']} questions, top-{args.top_k})"
    )
    for d in report["details"]:
        mark = "HIT " if d["hit"] else "miss"
        print(f"  [{mark}] {d['q']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
