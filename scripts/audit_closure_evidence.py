"""Audit whether the test references in closure receipts still RESOLVE.

The closure gate checks the FORM of an evidence citation (``path::name``); it
never checks that the citation points at anything. A rename turns a receipt
into prose, and nothing notices — found by the SENAR Rule 9.5 audit of session
#184 (closure-evidence-references-rot-and-nothing-notices).

Three design constraints, each paid for by measurement in session #186 rather
than argued:

* THE EXTRACTOR IS THE PRODUCT'S OWN. References come from
  ``service_ac_evidence.parse_evidence_lines`` — the same code the closure gate
  reads them with. A private regex here would make the audit and the gate two
  judges of one question (convention #301, stated in ``ac_evidence_detectors``).
  Measured: a hand-written ``tests/...py::name`` regex saw 474 citations where
  the product's ``TEST_REF_RE`` sees 5035, because the product also accepts a
  bare ``test_*.py`` and truncates ``file.py::Class::method`` at ``::Class``.

* RESOLUTION IS A NAMED POLICY. A bare file name is looked up across the test
  tree instead of being glued to the repo root. Measured: gluing produced 202
  false "file not found" out of 977 unique references (21%) — a report nobody
  would read twice.

* THERE IS NO SINGLE "BROKEN" NUMBER, AND THIS AUDIT REFUSES TO PRINT ONE.
  A citation that does not resolve has two utterly different causes, and git
  history separates them mechanically — with no exemption list of task slugs:
    - the target WAS in history and is gone now  -> ROTTED (rename or delete
      after closure). The reference decayed; the coverage may well be intact.
    - the target was NEVER in history            -> NEVER_EXISTED, a citation
      invented at closure time.
    - the target is a conventional EXAMPLE       -> ILLUSTRATIVE, quoted by a
      task whose SUBJECT is the citation format (``tests/foo.py``,
      ``tests/test_does_not_exist.py``). Split off in session #209 after a
      measurement: 13 of the 25 refs then in NEVER_EXISTED were examples and 3
      were genuine, so the headline over-reported real rot by a factor of two
      beside a ROTTED bucket of 22 that a reader was being taught to skim.
      They keep their own count instead of disappearing, because a number that
      silently drops entries is the next version of the same problem.
  Reporting them as one count would put ~10 permanent false alarms in every
  run, and a control that cries wolf stops being read (memory #404).

Read-only, and non-blocking BY DESIGN: renaming a test is a legitimate
operation. The point is that decay becomes VISIBLE, not that refactoring
becomes punished.

KNOWN LIMITATION, STATED RATHER THAN HIDDEN. Reconciling a finding does not
retire it. The cure for a rotted citation is an APPENDED note naming the
current address — the original receipt line is never rewritten, because a
closure receipt is a historical record. The stale citation therefore stays in
the corpus and keeps being reported: after the first reconciliation pass of
session #186, ``resolved`` rose from 945 to 950 while ROTTED stayed at 16.
So these counts are a FLOOR, not a health bar; what carries signal is the
DELTA between runs. Making a reconciled finding retire itself would need the
audit to read a task's later notes as an amendment of its earlier ones, which
is a separate design question and deliberately not answered here.

Public API:
    audit_closure_evidence(repo_root, tasks, ...) -> dict
"""

from __future__ import annotations

import ast
import difflib
import os
import subprocess
from typing import Any, Callable, Final, Iterable, Sequence

from illustrative_paths import is_illustrative, why_illustrative

# Verdicts. Named constants because the CLI, the tests and the report all speak
# them, and a typo in one of the three is exactly the silent failure this
# module exists to make loud.
RESOLVED: Final[str] = "resolved"
ROTTED: Final[str] = "rotted"
NEVER_EXISTED: Final[str] = "never_existed"
UNKNOWN_HISTORY: Final[str] = "unknown_history"
# A citation that is an EXAMPLE being quoted, not a file being cited — see
# `illustrative_paths`. Its own bucket rather than a silent drop: measured, 13
# of the 25 refs in NEVER_EXISTED were examples belonging to tasks whose very
# subject is fake or rotted citations, so the headline over-reported real rot
# by a factor of two. Hiding them would fix the number and lose the evidence
# that the number was ever wrong.
ILLUSTRATIVE: Final[str] = "illustrative"

_DEFAULT_TEST_ROOTS: Final[tuple[str, ...]] = ("tests",)
# difflib cutoff. 0.6 is the stdlib default and was measured on this corpus: it
# proposed a plausible successor for 10 of 17 name misses and proposed nothing
# for the rest, rather than inventing a neighbour for every miss.
_SUCCESSOR_CUTOFF: Final[float] = 0.6


def extract_refs(notes: str) -> list[str]:
    """Citations in one set of task notes, read exactly as the closure gate reads them."""
    if not notes:
        return []
    from service_ac_evidence import parse_evidence_lines

    return [ref for line in parse_evidence_lines(notes) for ref in line.test_refs]


def index_test_files(
    repo_root: str, test_roots: Sequence[str] = _DEFAULT_TEST_ROOTS
) -> dict[str, list[str]]:
    """Map base name -> repo-relative paths, for resolving a citation with no directory."""
    out: dict[str, list[str]] = {}
    for root in test_roots:
        base = os.path.join(repo_root, root)
        for dirpath, _dirnames, filenames in os.walk(base):
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, name), repo_root).replace("\\", "/")
                out.setdefault(name, []).append(rel)
    for paths in out.values():
        paths.sort()
    return out


def resolve_path(repo_root: str, rel: str, index: dict[str, list[str]]) -> tuple[str | None, bool]:
    """Return (repo-relative path or None, ambiguous?).

    A citation carrying a directory is taken literally. A bare file name is
    looked up in the test-tree index; two hits are reported as ambiguous rather
    than silently resolved to the first, because "which of the two did the
    closure mean" is a question this audit is not entitled to answer.
    """
    if os.path.exists(os.path.join(repo_root, rel)):
        return rel.replace("\\", "/"), False
    hits = index.get(os.path.basename(rel), [])
    if len(hits) == 1:
        return hits[0], False
    if len(hits) > 1:
        return hits[0], True
    return None, False


def member_segments(member: str) -> list[str]:
    """The names a node id asks of a module, in order: `TestA::test_b[en]` -> [TestA, test_b].

    The extractor reads a citation whole since GitLab #16 — class chain and
    parametrised id included — and a lookup of `TestA::test_b` as ONE name
    matched nothing, so 872 committed tests were reported as never having
    existed (session #257). The `[param]` suffix is pytest's, not the
    module's: it is cut at the first bracket BEFORE the split, because an id
    may itself carry `::` (`test_x[tests/a.py::b]`). No regex, by convention
    #301 — the citation parser is the product's, this is a split.
    """
    head = member.split("[", 1)[0]
    return [seg.strip() for seg in head.split("::") if seg.strip()]


_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def module_of(path: str) -> ast.Module | None:
    """The parsed module, or None if it cannot be read — never a guess about it."""
    try:
        with open(path, encoding="utf-8") as fh:
            return ast.parse(fh.read())
    except (OSError, SyntaxError, ValueError):
        return None


def names_in(path: str) -> set[str] | None:
    """Every def/async def/class name in a module, or None if it cannot be read."""
    tree = module_of(path)
    return None if tree is None else _flat_names(tree)


def _flat_names(tree: ast.AST) -> set[str]:
    return {node.name for node in ast.walk(tree) if isinstance(node, _DEFS)}


def _child_named(scope: ast.AST, name: str) -> ast.AST | None:
    """A def/class named `name` DIRECTLY in `scope`'s body — the chain's next link."""
    for node in getattr(scope, "body", ()):
        if isinstance(node, _DEFS) and node.name == name:
            return node
    return None


def missing_in_chain(tree: ast.Module, segments: list[str]) -> list[str]:
    """The segments the module does not define WHERE the chain says.

    `TestA::test_b` needs `test_b` in the body of `TestA`, not merely somewhere
    in the file: a flat lookup called `TestGroup::test_renamed_to_this` resolved
    when the method lived at module level (review, session #257). A single
    segment keeps the flat lookup — `file::test_x` for a method inside a class
    is honest shorthand, and was accepted before. Once the chain breaks, the
    remaining segments are checked flat: a leaf that exists nowhere is missing
    in its own right, so an invented method under a renamed class is not
    hidden behind the class's rot.
    """
    flat = _flat_names(tree)
    if len(segments) <= 1:
        return [seg for seg in segments if seg not in flat]
    missing: list[str] = []
    scope: ast.AST | None = tree
    for seg in segments:
        if scope is not None:
            child = _child_named(scope, seg)
            if child is not None:
                scope = child
                continue
            scope = None
            missing.append(seg)
        elif seg not in flat:
            missing.append(seg)
    return missing


def _git(repo_root: str, argv: list[str]) -> str | None:
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, shell=False
            ["git", *argv],
            cwd=repo_root,
            capture_output=True,
            text=True,
            # Explicit, because the default is the console code page: on Windows
            # `git log -S<name>` over this repo emits Cyrillic commit subjects
            # and cp1252 raised UnicodeDecodeError inside the reader thread,
            # which surfaced as five citations silently downgraded to
            # UNKNOWN_HISTORY. An audit that quietly says "cannot tell" when it
            # actually crashed is the failure mode this module was written
            # against — measured session #186, before the first CLI wiring.
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def git_ever_had_file(repo_root: str, rel: str) -> bool | None:
    """Was this path ever added to the repository? None when git cannot answer."""
    out = _git(repo_root, ["log", "--all", "--oneline", "--diff-filter=A", "--", rel])
    if out is None:
        return None
    return bool(out.strip())


def git_ever_had_name(repo_root: str, rel: str, name: str) -> bool | None:
    """Did this identifier ever appear in this file? None when git cannot answer."""
    out = _git(repo_root, ["log", "--all", "--oneline", f"-S{name}", "--", rel])
    if out is None:
        return None
    return bool(out.strip())


GitProbe = Callable[[str, str, "str | None"], "bool | None"]


def default_probe(repo_root: str, rel: str, name: str | None) -> bool | None:
    if name is None:
        return git_ever_had_file(repo_root, rel)
    return git_ever_had_name(repo_root, rel, name)


def _history_verdict(probe: GitProbe | None, repo_root: str, rel: str, member: str | None) -> str:
    if probe is None:
        return UNKNOWN_HISTORY
    ever = probe(repo_root, rel, member)
    if ever is None:
        return UNKNOWN_HISTORY
    return ROTTED if ever else NEVER_EXISTED


# Worse first: a name history never held is a citation that was wrong when
# written; a name history once held has merely rotted since.
_VERDICT_RANK: Final[dict[str, int]] = {NEVER_EXISTED: 2, ROTTED: 1, UNKNOWN_HISTORY: 0}


def _classify(
    repo_root: str,
    ref: str,
    index: dict[str, list[str]],
    name_cache: dict[str, ast.Module | None],
    probe: GitProbe | None,
) -> dict[str, Any]:
    rel, _, member = ref.partition("::")
    path, ambiguous = resolve_path(repo_root, rel, index)
    finding: dict[str, Any] = {
        "ref": ref,
        "verdict": RESOLVED,
        "path": path,
        "ambiguous": ambiguous,
        "successor_candidate": None,
    }
    if path is None:
        # Asked BEFORE git: an example name has no history to look up, and
        # spending a `git log -S` on it is how the sweep got slow as well as
        # wrong. A ref that RESOLVES is never illustrative — a real file at a
        # real path is a citation whatever it is called.
        if is_illustrative(ref):
            finding["verdict"] = ILLUSTRATIVE
            finding["illustrative_reason"] = why_illustrative(ref)
            return finding
        finding["verdict"] = _history_verdict(probe, repo_root, rel, None)
        return finding
    if not member:
        return finding
    if path not in name_cache:
        name_cache[path] = module_of(os.path.join(repo_root, path))
    tree = name_cache[path]
    if tree is None:
        # An unreadable module is not evidence of rot: say nothing rather than
        # accuse. tree is None only for a syntax error or an I/O failure.
        return finding
    # A member with no name in it (`[en]` alone) is asked of git as written,
    # never read as an empty — and therefore verified — chain.
    missing = missing_in_chain(tree, member_segments(member) or [member])
    if not missing:
        return finding
    # Every missing segment is asked of git, and the WORST answer is the
    # verdict: a renamed class does not excuse an invented method under it.
    # The successor is offered for the segment that decided the verdict.
    verdicts = [(seg, _history_verdict(probe, repo_root, path, seg)) for seg in missing]
    lost, verdict = max(verdicts, key=lambda sv: _VERDICT_RANK[sv[1]])
    finding["verdict"] = verdict
    finding["missing_segments"] = missing
    names = _flat_names(tree)
    near = difflib.get_close_matches(lost, sorted(names), n=1, cutoff=_SUCCESSOR_CUTOFF)
    finding["successor_candidate"] = near[0] if near else None
    return finding


def audit_closure_evidence(
    repo_root: str,
    tasks: Iterable[dict[str, Any]],
    *,
    test_roots: Sequence[str] = _DEFAULT_TEST_ROOTS,
    probe: GitProbe | None = default_probe,
) -> dict[str, Any]:
    """Resolve every closure citation in ``tasks`` and classify what fails.

    ``tasks`` are task rows (``slug`` + ``notes``) — the caller decides which
    ones, so the CLI can pass closed tasks and a test can pass two literals.
    ``probe=None`` disables the git question: every unresolved citation then
    lands in UNKNOWN_HISTORY instead of being guessed at.
    """
    index = index_test_files(repo_root, test_roots)
    name_cache: dict[str, ast.Module | None] = {}
    per_ref: dict[str, dict[str, Any]] = {}
    scanned = with_refs = total = 0

    for task in tasks:
        scanned += 1
        refs = extract_refs(task.get("notes") or "")
        if refs:
            with_refs += 1
        for ref in refs:
            total += 1
            entry = per_ref.get(ref)
            if entry is None:
                entry = _classify(repo_root, ref, index, name_cache, probe)
                entry["tasks"] = []
                per_ref[ref] = entry
            slug = task.get("slug") or "?"
            if slug not in entry["tasks"]:
                entry["tasks"].append(slug)

    findings = [e for e in per_ref.values() if e["verdict"] != RESOLVED]
    findings.sort(key=lambda e: (e["verdict"], e["ref"]))
    counts = {
        verdict: sum(1 for e in findings if e["verdict"] == verdict)
        for verdict in (ROTTED, NEVER_EXISTED, UNKNOWN_HISTORY, ILLUSTRATIVE)
    }
    return {
        "tasks_scanned": scanned,
        "tasks_with_refs": with_refs,
        "refs_total": total,
        "refs_unique": len(per_ref),
        "resolved_unique": len(per_ref) - len(findings),
        "counts": counts,
        "findings": findings,
    }


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
