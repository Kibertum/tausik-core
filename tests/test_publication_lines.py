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
from functools import lru_cache
from pathlib import Path

import pytest

from conftest import DORMANT_ON_PUBLIC_SNAPSHOT, IS_PUBLIC_SNAPSHOT

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

_SCAN_PATTERNS = {
    "reader premise": re.compile(r"CROSSCUTTING_SCOPE"),
    **_FORBIDDEN,
    **{label: spec[0] for label, spec in _DECLARED_REMAINDER.items()},
}


@lru_cache(maxsize=1)
def _tracked() -> tuple[str, ...]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    return tuple(line for line in out.splitlines() if line)


@lru_cache(maxsize=1)
def _scan_publication_tree() -> dict[str, tuple[str, ...]]:
    hits: dict[str, list[str]] = {label: [] for label in _SCAN_PATTERNS}
    for rel in _tracked():
        if rel in _MAY_DESCRIBE_LEAKS:
            continue
        try:
            text = (_REPO / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable: not a text leak
        for label, rx in _SCAN_PATTERNS.items():
            if rx.search(text):
                hits[label].append(rel)
    return {label: tuple(paths) for label, paths in hits.items()}


def test_publication_tree_has_a_reader_and_respects_all_leak_boundaries():
    """One tree walk keeps the premise, zero ratchets and declared ceilings."""
    tracked = _tracked()
    assert len(tracked) > 1000, f"only {len(tracked)} tracked files — git ls-files failed?"
    hits = _scan_publication_tree()
    assert hits["reader premise"]
    for label in sorted(_FORBIDDEN):
        offenders = hits[label]
        assert not offenders, (
            f"{label} is back in {len(offenders)} tracked file(s): {offenders[:5]}. "
            "Publication carries the whole tracked tree to a public remote, and "
            "session #180 counted 12 and 44 files of these two before they were "
            "cleaned. Zero is a measured state, not an aspiration."
        )
    if IS_PUBLIC_SNAPSHOT:
        pytest.skip(DORMANT_ON_PUBLIC_SNAPSHOT)
    for label in sorted(_DECLARED_REMAINDER):
        _rx, ceiling = _DECLARED_REMAINDER[label]
        offenders = hits[label]
        assert len(offenders) <= ceiling, (
            f"{label} now appears in {len(offenders)} tracked files, above the "
            f"declared {ceiling}. New: {sorted(set(offenders))[:5]}. This class is "
            "not cleaned, but it is not allowed to spread — either remove the new "
            "occurrence or move the pin down together with a measurement."
        )
        assert len(offenders) >= ceiling - 10, (
            f"{label} is down to {len(offenders)} files against a pin of {ceiling}. "
            "Move the pin down to lock the improvement in."
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

    def test_both_language_pages_exist_and_agree_about_remote_roles(self):
        for rel in ("docs/ru/publishing.md", "docs/en/publishing.md"):
            path = _REPO / rel
            assert path.is_file(), f"{rel} is missing — the procedure is back to living in memory"
            text = path.read_text(encoding="utf-8")
            assert "#267" in text, f"{rel} does not name the decision it executes"
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

    def test_only_local_git_ls_files_subprocess_is_used(self):
        import ast

        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in self._NETWORKY:
                raise AssertionError(f"this check calls {name}() — it must stay offline")
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
