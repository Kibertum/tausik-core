"""One coverage gate, in place of a hand-written test per kind of thing.

WHAT IT CHECKS: every name the framework SHIPS is named in the document a reader
would go to. Today that is the CLI commands against `docs/{ru,en}/cli.md`; the
shape generalises to any (live registry, document) pair without a new test.

MEASURED WHEN THIS LANDED (session #235): of the 53 commands the parser
declares, 14 appeared nowhere in `docs/ru/cli.md` and 14 nowhere in
`docs/en/cli.md`. Two of them — `graph` and `symbol` — had been added by this
very release, with dedicated documentation pages, and still never reached the
command reference. A command an agent cannot discover is a command nobody uses:
that was measured last release at 2 uses against 226 greps.

WHAT IT DOES NOT CHECK, said here so nobody reads more into a green run: this
gate sees whether a name is MENTIONED, not whether what is written about it is
true. A sentence that is correct about every name and wrong about the behaviour
passes. Claiming otherwise would repeat the exact defect the gate exists against
— a statement wider than what was done.

WHY NOT "resolve every backticked name": that was tried and refuted by
measurement in the same session (dead end #663). Backticks in this codebase mean
"a name in the system" — a config key, a status value, a column, a subcommand,
or a deliberately historical mention of something removed. Of 2,689 such
mentions only a handful could even be candidates, and all of those turned out to
be intentional. A gate firing on 821 legitimate places is a gate switched off.
"""

from __future__ import annotations

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: Doctor labels that are not user-facing checks.
_NOT_A_CHECK = {"caveman interop"}

#: A label may be worded differently in prose than in the terminal. Map only
#: where the document legitimately says it another way; no entry means the
#: document is expected to use the label verbatim.
_DOCTOR_ALIASES: dict[str, tuple[str, ...]] = {
    "Kilo MCP config": ("Kilo",),
    "OpenCode config": ("OpenCode",),
    "Brain config": ("Brain",),
    "Verify-First profile": ("Verify-First",),
    "Config trust tier": ("Trust tier", "trust tier"),
    "MCP server (project)": ("MCP",),
    "MCP server (brain)": ("MCP",),
    "Project DB": ("DB",),
    "Python venv": ("venv",),
    "Config knobs": ("Knobs", "knobs"),
    "Quality gates": ("gates",),
}

#: (what ships, where a reader looks, how a mention is recognised). Adding a
#: pair is how this gate grows — NOT by adding another test file, which is the
#: shape it replaced: one hand-written test per kind of thing, each re-deriving
#: the same idea and each able to go blind on its own.
COVERED: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("cli_commands", ("docs/ru/cli.md", "docs/en/cli.md"), "command"),
    ("doctor_checks", ("docs/ru/doctor.md", "docs/en/doctor.md"), "phrase"),
)


def _mentions(document: str, name: str) -> bool:
    """Is `name` named in `document` as a command, rather than as a substring?

    Two ways a document legitimately names a command, and both count:

      * on its own line, as in a code block — `db prune`;
      * inline after the wrapper, as in prose — "run `tausik db prune`".

    The second was missing at first and a test caught it: the gate demanded a
    line-anchored mention and would have called a perfectly documented command
    undocumented, which is the false refusal that gets a gate switched off.

    What must NOT count is a substring: `db` inside "database", `at` inside
    every sentence. That kind of match is what makes a coverage gate look green
    while covering nothing.
    """
    escaped = re.escape(name)
    line_anchored = re.compile(rf"(^|\n)\s*{escaped}(\s|$|\n|--)", re.MULTILINE)
    after_wrapper = re.compile(rf"(^|[\s`(]){escaped}(\s|$|\n|`|--)", re.MULTILINE)
    if line_anchored.search(document):
        return True
    for match in re.finditer(r"tausik\s+", document):
        if after_wrapper.match(document, match.end()) or after_wrapper.search(
            document, match.end() - 1, match.end() + len(name) + 2
        ):
            return True
    return False


def cli_commands() -> list[str]:
    """Live command names, from the parser rather than from a list."""
    from route_map import cli_commands as live

    return list(live())


def _doctor_sources() -> list[str]:
    """Every file a doctor check can print from — DERIVED, never listed.

    This was two named files once, and it went blind the day the optional checks
    moved into `service_doctor_external.py`: seven labels left the guard's view
    while the guard stayed green.
    """
    import glob

    found = [os.path.join(_HERE, "project_cli_doctor.py")]
    found += sorted(glob.glob(os.path.join(_HERE, "service_doctor_*.py")))
    return [p for p in found if os.path.isfile(p)]


def doctor_checks() -> list[str]:
    """Check labels `doctor` can print, read out of the source.

    Two shapes, because checks come in two: some print through the doctor's own
    printers, some hand a label back as a constant for the caller to print.
    """
    printed = re.compile(r"""(?:_?print_(?:ok|warn|fail))\(\s*["']([^"']+)["']""")
    constant = re.compile(r"""^_\w*LABEL\s*=\s*["']([^"']+)["']""", re.MULTILINE)
    found: set[str] = set()
    for path in _doctor_sources():
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        found |= set(printed.findall(text))
        found |= set(constant.findall(text))
    return sorted(label for label in found if label not in _NOT_A_CHECK)


def find_gaps(repo_root: str) -> list[tuple[str, str]]:
    """(name, document) for every shipped name missing from its document."""
    gaps: list[tuple[str, str]] = []
    sources = {"cli_commands": cli_commands, "doctor_checks": doctor_checks}
    for source, documents, style in COVERED:
        names = sources[source]()
        if not names:
            # Absence, not zero: a registry we could not read says nothing about
            # the documentation, and reporting "no gaps" would be a lie of the
            # kind this gate exists to catch (decision #334).
            continue
        for rel in documents:
            path = os.path.join(repo_root, rel)
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                gaps.append(("<the document itself>", rel))
                continue
            for name in sorted(names):
                if not _named(text, name, style):
                    gaps.append((name, rel))
    return gaps


def _named(document: str, name: str, style: str) -> bool:
    """Whether `name` is mentioned, in the way that KIND of name is written.

    Two styles, because a command and a prose label are recognised differently
    and one matcher for both would be wrong in one direction or the other: a
    substring test would let `db` pass on the word "database", while a
    line-anchored test would never find "Commit hooks" inside a sentence.
    """
    if style == "command":
        return _mentions(document, name)
    for candidate in (name, *_DOCTOR_ALIASES.get(name, ())):
        if candidate in document:
            return True
    return False


def check(repo_root: str) -> tuple[bool, str]:
    """(ok, message). The message names WHAT is missing and WHERE to write it."""
    gaps = find_gaps(repo_root)
    if not gaps:
        return True, "every shipped name is documented"

    by_document: dict[str, list[str]] = {}
    for name, rel in gaps:
        by_document.setdefault(rel, []).append(name)

    lines = [
        f"{len(gaps)} shipped name(s) are documented nowhere a reader would look. "
        "A command an agent cannot discover is a command nobody uses.",
    ]
    for rel, names in sorted(by_document.items()):
        lines.append(f"  {rel}: {', '.join(sorted(names))}")
    lines.append(
        "Add each to that file. This gate checks that the name is MENTIONED; "
        "what you write about it is on you."
    )
    return False, "\n".join(lines)


def run_doc_coverage_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Registry-uniform `(gate, files)` entrypoint.

    `files` is ignored, deliberately: narrowing to the task's declared scope
    would let a command added outside that scope close the task in silence, and
    a command nobody documented is exactly the kind nobody declares either.
    """
    root = os.path.dirname(_HERE)
    return check(root)


if __name__ == "__main__":  # pragma: no cover - exercised via the gate runner
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
