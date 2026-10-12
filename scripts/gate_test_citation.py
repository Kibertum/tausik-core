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

from gate_test_resolver import test_roots


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
    roots = [os.path.abspath(r) for r in test_roots(base)]
    # GitLab #16: a Rust/Go/TS project keeps tests beside the code and may have
    # no `tests/` root at all; a file NAMED as a test by its ecosystem
    # (`x_tests.rs`, `x_test.go`, `x.test.ts`, …) that exists inside the
    # project counts — the naming convention is the test-root equivalent there.
    # The traversal rule still holds: the file must lie inside the project.
    candidate = os.path.normpath(os.path.join(base, path))
    # Judged on the NORMALISED path relative to the project, never on the
    # citation as typed: `tests/../scripts/impl.py` is spelled with a test
    # directory in it and normalises to a source file — the traversal this
    # predicate closed once already must stay closed. Scoped the way root
    # discovery is: a `tests/` inside node_modules, a venv or an IDE profile is
    # not this project's (review, session #254). And a file that is merely
    # NAMED as a test, cited without a `::name`, must carry a test marker —
    # existence alone was the cheap citation this predicate exists to price.
    if os.path.isfile(candidate) and _inside(candidate, base):
        rel = os.path.relpath(candidate, base)
        if _named_as_a_test(rel) and not _in_a_skipped_dir(rel) and _carries_a_test(candidate, ref):
            return _named_test_defined(candidate, ref)
    if not roots:
        return False  # корней нет → цитату не с чем сверить → fail-closed

    if not os.path.isfile(candidate):
        # `test_foo.py` written without its directory — resolved ONLY внутри
        # корней с тестами, никогда как свободное имя где угодно в дереве.
        # Корни ОБНАРУЖИВАЮТСЯ, а не предполагаются равными `<base>/tests`:
        # у проекта с раскладкой backend/tests такая ссылка не разрешалась
        # вовсе, и честная цитата на существующий тест читалась как выдуманная.
        for tests_dir in roots:
            guess = os.path.normpath(os.path.join(tests_dir, os.path.basename(path)))
            if os.path.isfile(guess):
                candidate = guess
                break
        else:
            return False

    # Traversal check AFTER normalisation: `tests/../scripts/x.py` normalises
    # out of the test tree, and that is exactly what must not count. Проверяем
    # против ВСЕХ корней: файл обязан лежать внутри одного из них. Прежняя
    # редакция сверяла с единственной переменной цикла — при разрешении первой
    # веткой она осталась бы неопределённой (NameError), а при нескольких
    # корнях сверяла бы с последним просмотренным.
    if not any(_inside(candidate, r) for r in roots):
        return False
    return _named_test_defined(candidate, ref)


def _in_a_skipped_dir(rel: str) -> bool:
    """A path segment root discovery would not enter (vendored, venv, IDE)."""
    from gate_test_resolver import _discovery_skip

    parts = rel.replace("\\", "/").split("/")[:-1]
    return any(p in _discovery_skip() for p in parts)


#: What a test file of each ecosystem declares at least once. Read only when
#: the citation names no `::name` — then this is the whole content check.
_TEST_MARKER_RE = re.compile(
    r"(?:^\s*#\[test\]|^\s*#\[tokio::test\]"  # Rust
    r"|^\s*func\s+Test\w*\s*\("  # Go
    r"|^\s*(?:async\s+)?def\s+test_\w*\s*\("  # Python
    r"|\b(?:it|test|describe)\s*\(\s*[\"'`]"  # JS/TS
    r"|^\s*@Test\b"  # Java/Kotlin
    r"|^\s*(?:RSpec\.)?describe\b|^\s*it\s+[\"']"  # Ruby
    r"|^\s*\[(?:Test|Fact|Theory)\]|^\s*@testable|^\s*test\s*\(\s*[\"'])",  # C#/Swift/Dart
    re.MULTILINE,
)


def _carries_a_test(path: str, ref: str) -> bool:
    """With a `::name` the name check below is the content check; without one
    the file must declare at least one test in its ecosystem's idiom."""
    if "::" in ref:
        return True
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return _TEST_MARKER_RE.search(fh.read()) is not None
    except OSError:
        return False


def _named_as_a_test(path: str) -> bool:
    """True when the path, as written, is a test by the declared forms —
    `ac_evidence_detectors.TEST_REF_RE` matched whole, so the resolver and the
    detector cannot disagree on what a test file looks like."""
    from ac_evidence_detectors import TEST_REF_RE

    m = TEST_REF_RE.fullmatch(path.replace("\\", "/"))
    return m is not None


def _inside(path: str, root: str) -> bool:
    """True когда `path` лежит внутри `root`. Разные тома — не внутри."""
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False  # разные диски на Windows → commonpath бросает


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
    python = path.lower().endswith(".py")
    if not python:
        # Line comments are not declarations: `// TODO fn shadows_it` must not
        # satisfy a citation of ::shadows_it (review, session #254).
        source = re.sub(r"(?m)(?://|#|--)[^\n]*$", "", source)
    for segment in segments:
        name = segment.split("[", 1)[0].strip()
        if not name:
            continue
        if python:
            pattern = rf"^\s*(?:async\s+)?(?:def|class)\s+{re.escape(name)}\s*[(:]"
        else:
            # GitLab #16, other ecosystems: `fn name(`, `func name(`, `def name`
            # (Ruby), `public void name(`, `it("name"`, `test('name'`. The
            # floor is the same as Python's: the NAME must be declared or
            # quoted in the file, not merely mentioned in a comment.
            # The name must FOLLOW its declaration keyword — `fn name(`,
            # `func (r *T) name(`, `def name`, `void name(` — or be the STRING
            # ARGUMENT of a test-registration call. Sharing a line with the
            # keyword is not a declaration: `fn real() { log("name") }`.
            keywords = r"\b(?:fn|func|def|function|void)\b"
            receiver = r"(?:\([^)\n]*\)\s*)?"
            pattern = (
                rf"(?:{keywords}\s+{receiver}{re.escape(name)}\s*[(<:]?"
                rf"|\b(?:it|test|describe)\s*\(\s*[\"'`]{re.escape(name)}[\"'`])"
            )
        if not re.search(pattern, source, re.MULTILINE):
            return False
    return True
