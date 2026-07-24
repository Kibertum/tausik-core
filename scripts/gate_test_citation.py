"""Does an AC evidence citation name a real test — and where does `tests/` live?

Split out of `gate_ac_check` for the 400-line cap, along the seam its own review
exposed. "Has this criterion got evidence?" and "is this citation real?" are
different questions, and every defect found in the first version of the Rule 5
rewrite was in the second one: the `::name` was never looked at, `..` escaped the
test tree, a bare basename matched anything, and the root came from the process
cwd rather than from the project. Keeping them apart means the next change to
the gate does not have to re-read the path rules to be safe.
"""

from __future__ import annotations

import os
import re

def _project_root(root: str | None = None) -> str:
    """The project's root directory — NOT the directory the process stands in.

    `os.getcwd()` was used here, and it made the gate's verdict depend on where
    the agent happened to run the command from: identical task, `cwd=.` resolved
    the citation and `cwd=scripts` did not, so a task with genuine evidence was
    hard-blocked with "a path that does not resolve is treated as no evidence at
    all" and no `task log` line could fix it. The rest of the framework is
    deliberately cwd-independent (`find_tausik_dir` walks up ten levels); this
    predicate simply did not reuse it.
    """
    if root:
        return root
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return env
    try:
        from project_config import find_tausik_dir

        return os.path.dirname(os.path.abspath(find_tausik_dir()))
    except Exception:  # noqa: BLE001 — resolution is best-effort; cwd is the floor
        return os.getcwd()


def _test_ref_exists(ref: str, root: str | None = None) -> bool:
    """True when `tests/foo.py::test_bar` names a real test inside `tests/`.

    Fail-CLOSED: a reference that cannot be resolved does not count as evidence.
    An unresolvable citation is indistinguishable from an invented one, and this
    predicate's adversary is an agent that can write whatever it likes into its
    own notes.

    The first version checked `os.path.isfile` on the path and stopped there,
    which the review of that version defeated three ways: `tests/../scripts/
    gate_ac_check.py` escaped the test tree entirely and let the gate's OWN
    implementation file count as a test; a bare basename resolved against any of
    the ~300 files under `tests/`; and the `::name` was split off and never
    looked at, so an invented test function on a real file passed. All three are
    closed below — the path must normalise to somewhere inside `tests/`, and a
    named function must actually be defined in the file.

    What is still NOT checked, and is not claimed to be: that the test was ever
    run, that it passed, or that it has anything to do with this task. This
    predicate raises the price of a fabricated citation; it does not make one
    impossible, and an agent willing to write `def test_x(): pass` into a new
    file clears it. It is a floor, not a proof.
    """
    path = ref.split("::", 1)[0].strip()
    if not path:
        return False
    base = os.path.abspath(_project_root(root))
    tests_dir = os.path.join(base, "tests")
    candidate = os.path.normpath(os.path.join(base, path))
    if not os.path.isfile(candidate):
        # `test_foo.py` written without its directory — resolved ONLY inside
        # tests/, never as a free-floating name anywhere in the tree.
        candidate = os.path.normpath(os.path.join(tests_dir, os.path.basename(path)))
        if not os.path.isfile(candidate):
            return False
    # Traversal check AFTER normalisation: `tests/../scripts/x.py` normalises
    # out of the test tree, and that is exactly what must not count.
    if os.path.commonpath([candidate, tests_dir]) != tests_dir:
        return False
    return _named_test_defined(candidate, ref)


def _named_test_defined(path: str, ref: str) -> bool:
    """True when `ref`'s `::name` (if any) is defined in `path`.

    A citation with no `::name` is accepted — plenty of honest evidence names a
    file only — but a citation that DOES name a function is held to it, because
    inventing the name was free while the file was real.

    Every `::` segment is checked, because a pytest node id is
    `file::Class::method` and the first draft compared the whole tail against
    `def …`. That rejected `tests/test_hooks.py::TestBashFirewall::test_command`
    — a correct, copy-pasteable node id — which the measurement over this
    project's own closed tasks caught immediately. A parameterised id
    (`::test_x[case-3]`) keeps only the part before the bracket.
    """
    segments = [s.strip() for s in ref.split("::")[1:] if s.strip()]
    if not segments:
        return True
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError:
        return False  # unreadable → unverifiable → fail closed
    for segment in segments:
        name = segment.split("[", 1)[0].strip()
        if not name:
            continue
        if not re.search(
            rf"^\s*(?:async\s+)?(?:def|class)\s+{re.escape(name)}\s*[(:]",
            source,
            re.MULTILINE,
        ):
            return False
    return True

