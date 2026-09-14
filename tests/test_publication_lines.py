"""What leaves the tree when a release is published, held by a machine.

github-is-primary-by-decision-and-gitlab-is-primary-in-practice. Decision #267
settled the roles — GitLab develops, GitHub mirrors releases — after the 25.08
wording ("GitHub is the primary place of development") went unexecuted for five
sessions. The task's own closing line is what this file answers: a decision
executed by an agent's memory rather than by a mechanism is not executed.

PUBLICATION CARRIES THE WHOLE TRACKED TREE, `tausik/` included. Session #180
counted four classes of thing that must not go out; session #233 re-counted them
over 4,208 tracked files rather than trusting the earlier number:

    local path with the user's name   12 files -> 0
    other clients' project names      44 files -> 0
    internal host                     17 files -> 4 files (session #256)
    dev-machine path (D:\\Work)        not measured -> 22 files (session #256)

The first two are RATCHETS at zero. The last two are DECLARED REMAINDERS: they
are weaker — a directory layout and an internal address, not an identity — and
they live mostly inside the project's own accounting, so they are pinned at
their measured size and only GROWTH is red. Declaring a gap and holding it is
honest; pretending it is closed is not.

NO NETWORK. A check that needs the remote to be reachable fails exactly when it
is needed — before a publication, often from a machine that cannot reach it.
Everything here reads tracked files.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from conftest import DORMANT_ON_PUBLIC_SNAPSHOT, IS_PUBLIC_SNAPSHOT  # noqa: E402

_REPO = Path(__file__).resolve().parents[1]

CROSSCUTTING_SCOPE = ["docs/", "tausik/"]

#: A file that DESCRIBES a leak is not a leak. Kept narrow and named one by one:
#: widening the pattern instead would let a real occurrence hide behind a
#: plausible filename, and forbidding these would forbid writing about the
#: problem at all — which costs more than the problem.
_MAY_DESCRIBE_LEAKS = frozenset(
    {
        "docs/ru/publishing.md",
        "docs/en/publishing.md",
        "tests/test_publication_lines.py",
        # The task that neutralised 43 sample paths names the class in its
        # own journal — the "task about it" the paragraph above allows.
        "tausik/tasks/public-snapshot-is-a-filtered-tree-not-the-working-tree.md",
    }
)

#: Cleaned, and kept clean. A return is a defect, not a judgement call.
_FORBIDDEN = {
    "a local path carrying the user's name": re.compile(r"[Uu]sers[\\/]ayumashev", re.I),
    "another client's project name": re.compile(r"\b(hystolab|totoshkagame|kareta)\b", re.I),
}

#: Not cleaned. Pinned at the measured size so growth is visible; shrinking is
#: always allowed and the number is meant to come down.
_DECLARED_REMAINDER = {
    "internal host": (re.compile(r"gitlab\.yumash\.ru", re.I), 4),
    "dev-machine path": (re.compile(r"[Dd]:[\\/]{1,2}Work", re.I), 22),
}


def _tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def _files_matching(rx: re.Pattern[str]) -> list[str]:
    hits: list[str] = []
    for rel in _tracked():
        if rel in _MAY_DESCRIBE_LEAKS:
            continue
        try:
            text = (_REPO / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable: not a text leak
        if rx.search(text):
            hits.append(rel)
    return hits


class TestTheScanCanSeeAnything:
    """PREMISE. A scan that reads nothing passes every assertion below."""

    def test_the_tree_is_actually_enumerated(self):
        tracked = _tracked()
        assert len(tracked) > 1000, f"only {len(tracked)} tracked files — git ls-files failed?"

    def test_the_scan_finds_a_pattern_that_is_definitely_present(self):
        """Proves the reader works: this very file contains the word."""
        assert _files_matching(re.compile(r"CROSSCUTTING_SCOPE"))


class TestClassesThatWereCleanedStayClean:
    @pytest.mark.parametrize("label", sorted(_FORBIDDEN))
    def test_it_is_still_zero(self, label):
        offenders = _files_matching(_FORBIDDEN[label])
        assert offenders == [], (
            f"{label} is back in {len(offenders)} tracked file(s): {offenders[:5]}. "
            "Publication carries the whole tracked tree to a public remote, and "
            "session #180 counted 12 and 44 files of these two before they were "
            "cleaned. Zero is a measured state, not an aspiration."
        )


class TestDeclaredRemaindersDoNotGrow:
    """Declared, pinned, and allowed to shrink — never allowed to grow quietly."""

    @pytest.mark.parametrize("label", sorted(_DECLARED_REMAINDER))
    def test_the_count_has_not_grown(self, label):
        rx, ceiling = _DECLARED_REMAINDER[label]
        offenders = _files_matching(rx)
        assert len(offenders) <= ceiling, (
            f"{label} now appears in {len(offenders)} tracked files, above the "
            f"declared {ceiling}. New: {sorted(set(offenders))[:5]}. This class is "
            "not cleaned, but it is not allowed to spread — either remove the new "
            "occurrence or move the pin down together with a measurement."
        )

    @pytest.mark.parametrize("label", sorted(_DECLARED_REMAINDER))
    def test_the_pin_is_not_far_above_reality(self, label):
        if IS_PUBLIC_SNAPSHOT:
            # The pin is a statement about the development tree; on the
            # snapshot the remainder is zero by construction, which is the
            # claim tests/test_publication_snapshot.py makes for it.
            pytest.skip(DORMANT_ON_PUBLIC_SNAPSHOT)
        """A ceiling well above the truth is a ratchet that ratchets nothing.

        Not an equality: the count moves with ordinary work in `tausik/`, and a
        test that fails when the number goes DOWN teaches people to raise it.
        """
        rx, ceiling = _DECLARED_REMAINDER[label]
        actual = len(_files_matching(rx))
        assert actual >= ceiling - 10, (
            f"{label} is down to {actual} files against a pin of {ceiling}. Good — "
            "move the pin down to lock the improvement in."
        )


class TestNoDocumentClaimsGithubIsWhereDevelopmentHappens:
    """The 25.08 wording was replaced by #267. It must not come back as prose.

    An unexecuted promise in a document is worse than no document: five sessions
    pushed to GitLab while a decision said otherwise, and nothing noticed because
    nothing was watching the words.
    """

    _REPLACED = re.compile(
        r"(github[^\n]{0,40}(основн\w+ мест\w+ разработки|primary place of development)"
        r"|(основн\w+ мест\w+ разработки|primary place of development)[^\n]{0,40}github)",
        re.I,
    )

    def test_the_replaced_wording_appears_in_no_document(self):
        offenders = [
            rel
            for rel in _tracked()
            if rel.startswith(("docs/", "README"))
            and self._REPLACED.search((_REPO / rel).read_text(encoding="utf-8", errors="replace"))
        ]
        assert offenders == [], (
            f"these documents still call GitHub the place development happens: "
            f"{offenders}. Decision #267 replaced that wording after it went five "
            "sessions unexecuted; a document repeating it is an unkept promise."
        )

    def test_the_page_that_states_the_roles_exists_in_both_languages(self):
        for rel in ("docs/ru/publishing.md", "docs/en/publishing.md"):
            path = _REPO / rel
            assert path.is_file(), f"{rel} is missing — the procedure is back to living in memory"
            text = path.read_text(encoding="utf-8")
            assert "#267" in text, f"{rel} does not name the decision it executes"

    def test_both_language_versions_say_the_same_thing_about_the_roles(self):
        """Not a translation check — a check that the two do not disagree about
        WHICH remote develops and which mirrors."""
        ru = (_REPO / "docs/ru/publishing.md").read_text(encoding="utf-8")
        en = (_REPO / "docs/en/publishing.md").read_text(encoding="utf-8")
        for text, dev, mirror in (
            (ru, "линия разработки", "зеркало"),
            (en, "development line", "mirror"),
        ):
            gitlab_line = next(ln for ln in text.splitlines() if "GitLab" in ln and "|" in ln)
            github_line = next(ln for ln in text.splitlines() if "GitHub" in ln and "|" in ln)
            assert dev.lower() in gitlab_line.lower(), gitlab_line
            assert mirror.lower() in github_line.lower(), github_line


class TestTheCheckNeedsNoNetwork:
    """AC6. A precondition that needs the remote fails exactly when it matters.

    Asserted over this module's own AST rather than its text: a string mentioning
    a URL inside a docstring is not a network call, and a check that cannot tell
    those apart would forbid documenting what it checks.
    """

    _NETWORKY = {"urlopen", "urlretrieve", "get", "post", "request", "connect"}

    def test_no_call_here_reaches_out(self):
        import ast

        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in self._NETWORKY:
                raise AssertionError(f"this check calls {name}() — it must stay offline")

    def test_the_only_subprocess_is_git_ls_files(self):
        import ast

        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        argv_lists = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "run"
            for node in node.args[:1]
        ]
        assert argv_lists, "no subprocess found — the premise of this test is gone"
        for argv in argv_lists:
            words = [e.value for e in argv.elts if isinstance(e, ast.Constant)]
            assert words[:2] == ["git", "ls-files"], (
                f"an unexpected subprocess: {words}. Reading the working tree is "
                "local; anything else here would put the network on the path of a "
                "check whose whole job is to run before a publication."
            )
