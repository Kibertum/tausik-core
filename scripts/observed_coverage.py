"""What a test ACTUALLY touched, observed while it runs.

WHY OBSERVED AND NOT DERIVED. Test selection today maps `scripts/foo.py` to
`tests/test_foo.py` by NAME. That resolver is why `CROSSCUTTING_SCOPE` exists —
a hand-written patch for the cases where the names do not line up, declared by
hand four times in session #157 alone. Names cannot see dynamic dispatch,
monkeypatching, config-dependent behaviour, or the local-imports-inside-function-
bodies style this codebase uses throughout. A test run can.

WHY `sys.setprofile` AND NOT `coverage`. `coverage` is not installed and cannot
be: the project is stdlib-only by a hard constraint. Measured before writing
this: `sys.setprofile` fires and records exactly the files a call reaches —
`roots_for('.')` yielded `scripts/source_roots.py` and `scripts/ide_utils.py`,
and nothing else of ours. Function granularity, not line granularity, which is
all this needs: the question is WHICH FILE a test reached, never which line.

WHY A PYTEST PLUGIN AND NOT A GLOBAL HOOK. Installed before `pytest.main`, the
profiler does not survive into the tests — measured, and it reported zero files.
Installed around each test by a hook, it also answers the question that matters:
which TEST reached that file, not merely that somebody did.

OFF BY DEFAULT. Observation costs time on every test, and the ordinary run must
not pay for a graph it is not building. The environment variable is the switch,
and its absence is the normal case.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from typing import Any

#: Set to any non-empty value to observe. Absent — and that is the usual state —
#: nothing below runs at all.
ENV_FLAG = "TAUSIK_OBSERVE_COVERAGE"

#: Where the observation is written. One line per (test, file) pair, appended,
#: so a run under `-n auto` from several worker processes does not need a lock:
#: appends of a single short line are atomic enough on both platforms, and the
#: reader de-duplicates anyway.
ENV_OUTPUT = "TAUSIK_OBSERVE_OUTPUT"

_DEFAULT_OUTPUT = os.path.join(".tausik", "observed_coverage.jsonl")

#: Never recorded as touched: the framework's own state, caches, the deployed
#: IDE profiles (byte-copies of `scripts/`, which would double every edge) and
#: anything from site-packages. The TEST FILE ITSELF is deliberately NOT filtered
#: here — the observer records honestly what ran, and the ingestion step uses
#: that file as the edge's SOURCE rather than its target, so no self-edge is
#: ever stored. Filtering it here would have hidden the one file the ingestion
#: needs to identify the test by.
def _never_indexed() -> frozenset[str]:
    """Directory names never recorded, with the IDE profiles FROM THE REGISTRY.

    Spelling `.claude`, `.cursor`, `.qwen` here as literals would be a second
    list of the hosts, and `source_roots` already derives that list from
    `ide_utils.IDE_REGISTRY`. The guard that forbids new host literals in
    `scripts/` caught this module for exactly that, one session after it caught
    `source_roots.py` for the same thing — the second time is what makes it a
    pattern rather than a slip.
    """
    base = {".tausik", "__pycache__", ".git", "site-packages"}
    try:
        from source_roots import _ide_profile_dirs
    except Exception:  # noqa: BLE001 — observation must never break a run
        return frozenset(base)
    return frozenset(base | set(_ide_profile_dirs()))


_SKIP_DIR_PARTS = _never_indexed()


#: Never recorded either, by NAME rather than by directory. The docstring above
#: promised this and the first version did not do it: `observed_coverage.py` and
#: `conftest.py` appeared under all 22 tests of the trial run, because the filter
#: matched directory segments only. A file every test touches relates every
#: artifact to everything, which is precisely the noise that makes a graph
#: useless rather than merely incomplete.
_SKIP_FILES = frozenset({"scripts/observed_coverage.py", "tests/conftest.py"})

#: filename -> repo-relative path, or None for "not ours". DECIDED ONCE PER
#: FILENAME, and that is not a micro-optimisation. The hook fires on every
#: function call — millions of times in a full suite — while the number of
#: distinct `co_filename` values is in the hundreds. The first version called
#: `os.path.relpath` on each event, and a test died on a five-minute timeout
#: INSIDE `ntpath.relpath`, taking an xdist worker down with it ("node down:
#: Not properly terminated"). Measured after: one file's 22 tests went from
#: 14.5s to 8.7s against a 5.5s baseline.
#:
#: Module-level because the decisions are about PATHS, not about a test.
#: The TOUCHED set stays per-instance — sharing that one would be the
#: attribution bug `stop()` exists to prevent.
_VERDICTS: dict[str, str | None] = {}


def is_enabled() -> bool:
    return bool(os.environ.get(ENV_FLAG))


def output_path(project_dir: str) -> str:
    configured = os.environ.get(ENV_OUTPUT)
    if configured:
        return configured
    return os.path.join(project_dir, _DEFAULT_OUTPUT)


def _repo_relative(path: str, root: str) -> str | None:
    """`path` under `root` as a POSIX repo-relative path, or None.

    The absoluteness check is not a formality. A frame's `co_filename` is not
    always a path: frozen stdlib modules report `<frozen os>`, and `relpath`
    happily treats that as a relative name under the root, so the first run
    recorded `<frozen codecs>` as a repository file. A pseudo-path admitted here
    would become an artifact in the graph that no query could ever resolve.
    """
    if not os.path.isabs(path):
        return None
    try:
        rel = os.path.relpath(path, root)
    except (OSError, ValueError):
        return None
    if rel.startswith(".."):
        return None
    rel = rel.replace("\\", "/")
    if _SKIP_DIR_PARTS & set(rel.split("/")):
        return None
    if rel in _SKIP_FILES:
        return None
    return rel


class Observer:
    """Records the repo files reached between `start()` and `stop()`.

    One instance per test. `stop()` returns the set and forgets it, so a leaked
    instance cannot silently attribute one test's reach to the next.
    """

    def __init__(self, root: str) -> None:
        self._root = os.path.abspath(root)
        self._touched: set[str] = set()
        # Typed explicitly: inferred from `None` it would be `None`, and
        # restoring a real profiler into it would not type-check.
        self._previous: Callable[..., Any] | None = None
        # Shared across observers via the module-level cache below.
        self._verdict = _VERDICTS

    def _hook(self, frame, event, arg):  # noqa: ANN001 - the CPython profiler ABI
        filename = frame.f_code.co_filename
        try:
            rel = self._verdict[filename]
        except KeyError:
            rel = _repo_relative(filename, self._root)
            self._verdict[filename] = rel
        if rel is not None:
            self._touched.add(rel)
        return None

    def start(self) -> None:
        # The previous profiler is restored rather than dropped: pytest plugins
        # compose, and a profiler that evicts another one silently breaks
        # whatever installed it first.
        self._previous = sys.getprofile()
        sys.setprofile(self._hook)

    def stop(self) -> set[str]:
        sys.setprofile(self._previous)
        self._previous = None
        touched, self._touched = self._touched, set()
        return touched


def record(output: str, test_id: str, files: set[str]) -> None:
    """Append one line per (test, file). Never raises: observation is secondary.

    A failure here must not fail the test that was being observed — the run is
    the primary work and the graph is a by-product. The loss shows up as a file
    the graph does not know about, which the query layer already reports as
    absence rather than as coverage.
    """
    import json

    if not files:
        return
    try:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "a", encoding="utf-8") as fh:
            for rel in sorted(files):
                fh.write(json.dumps({"test": test_id, "file": rel}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read(output: str) -> Iterator[tuple[str, str]]:
    """(test_id, file) pairs from an observation file, skipping unreadable lines.

    A malformed line is skipped rather than fatal: the file is appended to by
    several worker processes, and one torn write must not throw away every
    observation beside it.
    """
    import json

    try:
        with open(output, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                test_id = row.get("test")
                rel = row.get("file")
                if isinstance(test_id, str) and isinstance(rel, str):
                    yield test_id, rel
    except OSError:
        return
