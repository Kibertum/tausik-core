"""CLI handler for `tausik graph` — build it, then ask it.

MEASURED BEFORE THIS EXISTED: `artifacts`, `artifact_symbols` and
`artifact_edges` held 0 rows each, in the repository that authored them, a day
after the substrate shipped. Nothing populated them and nothing could: the
service methods had no caller outside their own tests.

WHAT THIS PRINTS IS WHAT IT STORED, INCLUDING THE ZEROES. A build that produced
no edges says so and says why — a co-change layer over a repository with four
commits has almost nothing to observe, and that is a fact about the history, not
a failure of the build.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from service_artifact_graph import classify, fingerprint


#: Suffixes a symbol extractor exists for. Everything else is NOT a file
#: without symbols — it is a file we cannot read symbols out of.
SYMBOL_SUFFIXES = (".py", ".pyi")


def _root() -> str:
    return os.getcwd()


def _index_everything(svc: Any, root: str) -> tuple[list[str], list[str], str]:
    """Index every source file under the project's own roots.

    Returns the PATHS, not just their count: the caller needs the same list to
    say how many of them have no symbol extractor, and asking the database for
    it again would mean a new backend method under a ratchet that forbids one.
    """
    from source_roots import resolve

    roots, source = resolve(root)
    paths: list[str] = []
    for name in roots:
        base = os.path.join(root, name)
        if not os.path.isdir(base):
            continue
        for current, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not _skip_dir(d)]
            for filename in filenames:
                full = os.path.join(current, filename)
                rel = os.path.relpath(full, root).replace("\\", "/")
                paths.append(rel)
    svc.graph_index_paths(paths, root=root)
    return paths, list(roots), source


def index_symbols(svc: Any, root: str, paths: list[str]) -> dict[str, int]:
    """Fill `artifact_symbols` from the definitions the index already finds.

    WHY THIS EXISTS. Two half-graphs shipped a day apart and did not know about
    each other: `symbol_index` answered `tausik symbol` by re-walking the tree on
    every call, while `artifact_symbols` — a table built for exactly these rows —
    held zero.

    WHY IT LIVES IN THE CLI LAYER and not on `ProjectService`. That class is
    under a ratchet whose test pins its public surface at 148 members and forbids
    it to rise; the goal written into the baseline is that it comes DOWN. Adding
    a 149th for this would have been the growth the ratchet exists to stop, so
    the composition happens here, beside the command that needs it.

    Returns counts INCLUDING the files it could not read: "0 symbols" and "no
    extractor for this language" are different answers, and a Go project reading
    the first would conclude its own code has no definitions (decisions #334,
    #349).
    """
    from symbol_index import build_index, roots_for

    roots, _source = roots_for(root)
    written = 0
    for symbol in build_index(root, roots):
        artifact = svc.be.artifact_get(symbol.path)
        if not artifact:
            # Only symbols of artifacts the graph already knows: indexing a file
            # here as a side effect would put rows in the graph that the build
            # never counted.
            continue
        if svc.be.artifact_symbol_add(int(artifact["id"]), symbol.qualname, symbol.lineno):
            written += 1

    from service_artifact_graph import classify

    unreadable = sum(
        1
        for path in paths
        if classify(path) in ("code", "config")
        and not path.lower().endswith(SYMBOL_SUFFIXES)
    )
    return {"symbols": written, "no_extractor": unreadable}


def ingest_observed(svc: Any, root: str) -> dict[str, int]:
    """Turn an observation file into `covers` edges. Returns what it wrote.

    THE EDGE POINTS FROM THE TEST FILE TO THE FILE IT REACHED, and its layer is
    `observed_coverage` — a record of what happened, distinct from an inference
    out of git history and from somebody's declaration. The graph's whole
    discipline is that those three never share a number.

    Confidence is 1.0, and unlike the co-change layer that is not a shortcut:
    the test DID run and it DID reach that file. `observations` carries how many
    tests in that file reached it, which is the number that says how central the
    relationship is.

    A self-edge is never stored. The observer records the test file honestly —
    it is the file the test lives in — and this is where that fact becomes the
    edge's SOURCE rather than one of its targets.
    """
    from observed_coverage import output_path, read

    path = output_path(root)
    if not os.path.isfile(path):
        return {"pairs": 0, "edges": 0, "tests": 0}

    # (test file, reached file) -> how many test FUNCTIONS in that file reached it.
    counts: dict[tuple[str, str], int] = {}
    tests: set[str] = set()
    for test_id, reached in read(path):
        test_file = test_id.split("::", 1)[0].replace("\\", "/")
        if not test_file or test_file == reached:
            continue
        tests.add(test_id)
        counts[(test_file, reached)] = counts.get((test_file, reached), 0) + 1

    written = 0
    for (test_file, reached), observations in counts.items():
        if not os.path.isfile(os.path.join(root, test_file)):
            continue
        if not os.path.isfile(os.path.join(root, reached)):
            continue
        src = svc.be.artifact_upsert(test_file, classify(test_file), fingerprint(test_file, root))
        dst = svc.be.artifact_upsert(reached, classify(reached), fingerprint(reached, root))
        if src == dst:
            continue
        svc.be.artifact_edge_add(
            src, dst, "covers", "observed_coverage", 1.0,
            observations=observations, source_ref=path,
        )
        written += 1
    return {"pairs": len(counts), "edges": written, "tests": len(tests)}


def _skip_dir(name: str) -> bool:
    from source_roots import _NEVER

    return name in _NEVER


def cmd_graph(svc: Any, args: Any) -> None:
    """Dispatch `graph build|show|status`."""
    sub = getattr(args, "graph_cmd", None)
    if sub == "build":
        _build(svc, args)
    elif sub == "show":
        _show(svc, args)
    elif sub == "read":
        _read(args)
    elif sub == "snapshot":
        _snapshot(args)
    elif sub == "diff":
        _diff(args)
    elif sub == "status":
        _status(svc)
    else:
        print(
            "error: say what to do — `graph build`, `graph show <path>`, "
            "`graph read <path>`, `graph snapshot <label>`, "
            "`graph diff <before> <after>` or `graph status`",
            file=sys.stderr,
        )
        sys.exit(1)


def _build(svc: Any, args: Any) -> None:
    """Build in ONE transaction, and say how long it took.

    MEASURED: the first working build of this repository wrote roughly 22,000
    rows in 2 minutes 27 seconds — about 6.7 ms each, because the database runs
    WAL with `synchronous=FULL` and every autocommitted statement pays an fsync.
    The same work against a fresh database took 4.3 s. Nothing about the graph
    was slow; the commit boundary was in the wrong place.

    A build nobody will run twice is a build nobody runs, and the framework then
    ships a graph that is empty everywhere except where somebody was patient —
    which is the defect this whole task exists to remove.
    """
    import time

    root = _root()
    layer = getattr(args, "layer", "all") or "all"
    started = time.perf_counter()

    from source_roots import describe

    with svc.be.transaction():
        if getattr(args, "rebuild", False):
            removed = svc.be.graph_clear()
            print(f"cleared: {removed} artifact(s) and everything hanging off them")

        paths, roots, source = _index_everything(svc, root)
        print(describe(roots, source))
        print(f"indexed: {len(paths)} artifact(s)")

        symbols = index_symbols(svc, root, paths)
        print(f"symbols: {symbols['symbols']} from files this framework can parse")
        if symbols["no_extractor"]:
            # ABSENCE, NAMED. Saying nothing here would let a Go or Terraform
            # project read "0 symbols" as "my code has none" rather than "this
            # framework has no extractor for it yet" (decisions #334, #349).
            print(
                f"  {symbols['no_extractor']} source file(s) have NO symbol extractor here — "
                "Python only in 1.9. Their co-change and declared edges are built as usual."
            )

        if layer in ("all", "cochange"):
            window = getattr(args, "window", None)
            kwargs = {"window": int(window)} if window else {}
            n = svc.graph_build_cochange(root=root, **kwargs)
            print(f"co-change edges (from git history): {n}")
            if n == 0:
                # A zero that names its cause. Silence here would read as "the
                # layer is broken" when the honest reading is "this history has
                # nothing to observe yet" — two states an operator must be able
                # to tell apart.
                print(
                    "  none — the layer needs a file pair appearing together in at "
                    "least two commits within the window"
                )

        if layer in ("all", "observed"):
            seen = ingest_observed(svc, root)
            print(
                f"observed edges (from a test run): {seen['edges']} "
                f"({seen['tests']} test(s) recorded)"
            )
            if seen["edges"] == 0:
                # Absence, with its cause. "No observation file" and "the run
                # reached nothing" are different facts, and only the first is
                # the ordinary state of a fresh checkout.
                print(
                    "  none — run the suite once with TAUSIK_OBSERVE_COVERAGE=1 to record "
                    "which test reaches which file"
                )

        if layer in ("all", "declared"):
            n = svc.graph_build_declared(root=root)
            print(f"declared edges (from this project's own statements): {n}")
            if n == 0:
                print("  none — no CROSSCUTTING_SCOPE in tests and no task declared relevant_files")

    print(f"built in {time.perf_counter() - started:.1f}s")


def _show(svc: Any, args: Any) -> None:
    root = _root()
    path = str(getattr(args, "path", "") or "").replace("\\", "/")
    answer = svc.neighbours_of(path, root=root)

    if getattr(args, "json", False):
        print(json.dumps(answer, ensure_ascii=False, indent=2))
        return

    if not answer.get("known"):
        print(
            f"{path}: not in the graph. Run `tausik graph build` — or the path is "
            "outside this project's source roots."
        )
        return

    edges = answer.get("edges") or []
    print(f"{path}  (indexed {answer.get('indexed_at')})")
    _print_symbols(svc, path)
    if answer.get("partially_stale"):
        # Named, never implied. A stale answer that looks fresh is the one
        # outcome this graph exists to avoid.
        print(f"  STALE — these have changed since indexing: {', '.join(answer['stale'])}")
    if not edges:
        print("  no edges. Nothing in this project has been observed or declared alongside it.")
        return
    for edge in edges:
        arrow = "->" if edge["direction"] == "out" else "<-"
        print(
            f"  {arrow} {edge['target']}  [{_layer_in_words(edge['layer'])}, "
            f"confidence {edge['confidence']:.2f}, {edge['observations']} observation(s)]"
        )


#: The layer, said in words rather than in the vocabulary. The stored `relation`
#: for a declared grouping is `co_changes` — deliberately, because a task's
#: `relevant_files` states "these were worked on together" and NOT "one mentions
#: the other" (see `_declared_from_tasks`). Printing the raw pair read as a
#: contradiction: `[co_changes, declared_relevant_files]` looks like an
#: observation labelled a declaration. The vocabulary is right; showing it to a
#: reader who has not read the schema was not.
_LAYER_IN_WORDS = {
    "git_cochange": "observed together in git history",
    "declared_crosscutting": "declared: a test names this in CROSSCUTTING_SCOPE",
    "declared_relevant_files": "declared: worked on together in one task",
    "declared_scope_paths": "declared: inside one task's scope",
}


def _layer_in_words(layer: str) -> str:
    return _LAYER_IN_WORDS.get(layer, layer)


#: How many definitions `graph show` lists before saying how many more there
#: are. The same bound, for the same reason, as `tausik symbol`: past this the
#: answer stops being cheaper than opening the file, which is its whole point.
MAX_SYMBOLS_SHOWN = 12


def _print_symbols(svc: Any, path: str) -> None:
    """What this file DEFINES, read from the rows `graph build` already wrote.

    The rows existed before this did — 13,312 of them on this repository — and
    nothing read them back: `symbols_for_artifact` had no caller anywhere in the
    tree. Storing and never reading is the same defect as building and never
    invoking, one level down.

    SILENT when there are none, rather than printing an empty heading. A file
    the framework has no extractor for — markdown, terraform — would otherwise
    read as "defines nothing", which is a different claim from "we cannot read
    its definitions" (decisions #334, #349).
    """
    try:
        artifact = svc.be.artifact_get(path)
        if not artifact:
            return
        symbols = svc.be.symbols_for_artifact(int(artifact["id"]))
    except Exception:  # noqa: BLE001 - a display extra must not break the answer
        return
    if not symbols:
        return
    shown = symbols[:MAX_SYMBOLS_SHOWN]
    names = ", ".join(f"{s['name']}:{s['line']}" for s in shown)
    more = len(symbols) - len(shown)
    tail = f" (+{more} more)" if more > 0 else ""
    print(f"  defines: {names}{tail}")


def _read(args: Any) -> None:
    """`graph read <path>` — the navigation answer, ranked and bounded."""
    from graph_navigation import DEFAULT_BUDGET, answer

    path = str(getattr(args, "path", "") or "")
    limit = getattr(args, "limit", None)
    print(
        answer(
            _root(),
            path,
            direction="affects" if getattr(args, "affects", False) else "read",
            budget=int(limit) if limit else DEFAULT_BUDGET,
        )
    )


def _snapshot(args: Any) -> None:
    from graph_snapshot import write

    label = str(getattr(args, "label", "") or "")
    if not label:
        print("error: give the snapshot a label, usually a release tag", file=sys.stderr)
        sys.exit(1)
    path, edges, size = write(_root(), label)
    rel = os.path.relpath(path, _root()).replace("\\", "/")
    print(f"snapshot '{label}': {edges} edge(s) -> {rel} ({size // 1024} KB)")


def _diff(args: Any) -> None:
    from graph_snapshot import collect, diff, read, render

    root = _root()
    before_label = str(getattr(args, "before", "") or "")
    after_label = str(getattr(args, "after", "") or "")

    before = read(root, before_label)
    if before is None:
        # NOT an empty diff. A snapshot that does not exist says nothing about
        # the relations, and rendering "no changes" would be a confident lie.
        print(
            f"error: no snapshot named '{before_label}' — take one with "
            f"`tausik graph snapshot {before_label}`",
            file=sys.stderr,
        )
        sys.exit(1)

    if after_label == "now":
        after = collect(root)
    else:
        # Narrowed before use rather than after: `read` may answer None, and the
        # branch below is the only place that state is legitimate.
        stored = read(root, after_label)
        if stored is None:
            print(
                f"error: no snapshot named '{after_label}' — take one, or pass `now` "
                "to compare against the live graph",
                file=sys.stderr,
            )
            sys.exit(1)
        after = stored

    print(render(before_label, after_label, diff(before, after)))


def _status(svc: Any) -> None:
    root = _root()
    from source_roots import describe, resolve

    roots, source = resolve(root)
    print(describe(roots, source))

    counts = svc.be.graph_counts()
    print(
        f"stored: {counts['artifacts']} artifact(s), {counts['symbols']} symbol(s), "
        f"{counts['edges']} edge(s)"
    )
    if not counts["artifacts"]:
        print("  the graph is empty — `tausik graph build` fills it")
        return
    stale = svc.graph_stale_artifacts(root=root)
    print(f"stale: {len(stale)} artifact(s) no longer match what was indexed")
    for item in stale[:10]:
        print(f"  {item['path']}")
    if len(stale) > 10:
        print(f"  ... and {len(stale) - 10} more")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
