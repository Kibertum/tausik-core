"""One changelog file per task, instead of every task editing the same two lines.

WHY. The continuous-changelog gate asks each closing task for an added line in
`CHANGELOG.md` AND `CHANGELOG.ru.md`, and every entry goes to the head of the same
`[Unreleased]` section. With parallel lanes that is a conflict on EVERY closed task in both
languages — not occasionally, but always, because everyone writes into the first lines of
one section. Of the three shared files a lane touches, this is the only one that conflicts
every time: migrations conflict only for the lane that changes the schema, and the
generated constants are rebuilt on merge.

A fragment cannot conflict by construction — it is named after the task. The pattern is
towncrier's; the implementation is ours and stdlib-only, like the rest of the project.

BOTH LANGUAGES IN ONE FILE. The project ships a pair, and half a pair is not an entry. Two
files per task would let one language be forgotten in exactly the way the parity test
exists to catch, so the fragment carries both and is refused without either.

THE GATE DID NOT GET WEAKER. It accepts a second proof, not a smaller one: a fragment that
is missing, empty or half-written is refused, and a task with neither a fragment nor a line
in the shared files is refused exactly as before.
"""

from __future__ import annotations

import os
import re
from typing import Final, NamedTuple

#: Where a task's own entry lives. One file per task: the name is the slug, so two lanes
#: cannot write the same path.
FRAGMENT_DIR: Final[str] = "changelog.d"

#: Marks which language the text below it is in. A comment, so the fragment stays readable
#: markdown and renders as nothing if anyone opens it in a viewer.
LANG_MARK: Final[re.Pattern[str]] = re.compile(r"^<!--\s*lang:\s*(ru|en)\s*-->\s*$", re.M)

#: The shared files each language folds into, in the order they are written.
TARGETS: Final[dict[str, str]] = {"en": "CHANGELOG.md", "ru": "CHANGELOG.ru.md"}

#: The heading a fragment is folded under.
UNRELEASED: Final[str] = "## [Unreleased]"


class MalformedFragment(ValueError):
    """A fragment that cannot be read. Assembly stops rather than dropping it silently."""


class Fragment(NamedTuple):
    slug: str
    path: str
    #: {"en": text, "ru": text}
    text: dict[str, str]


def fragment_path(root: str, slug: str) -> str:
    return os.path.join(root, FRAGMENT_DIR, f"{slug}.md")


def parse(raw: str, where: str) -> dict[str, str]:
    """{lang: text} from one fragment's contents.

    Raises `MalformedFragment` naming the file. A fragment that cannot be parsed is not an
    empty one: dropping it would take a shipped change out of the release notes while every
    gate stayed green, which is the failure this project names a silent error.
    """
    marks = list(LANG_MARK.finditer(raw))
    if not marks:
        raise MalformedFragment(
            f"{where}: no language marker. A fragment names its languages with "
            "`<!-- lang: en -->` and `<!-- lang: ru -->` so the pair cannot drift apart."
        )
    out: dict[str, str] = {}
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        lang = mark.group(1)
        if lang in out:
            raise MalformedFragment(f"{where}: language '{lang}' appears twice.")
        out[lang] = raw[mark.end() : end].strip()
    return out


def check(root: str, slug: str) -> tuple[bool, str]:
    """(ok, reason). The gate's question, answered against the fragment alone."""
    path = fragment_path(root, slug)
    if not os.path.isfile(path):
        return False, f"no fragment at {FRAGMENT_DIR}/{slug}.md"
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        return False, f"{FRAGMENT_DIR}/{slug}.md could not be read: {exc}"
    if not raw.strip():
        return False, f"{FRAGMENT_DIR}/{slug}.md is empty"
    try:
        text = parse(raw, f"{FRAGMENT_DIR}/{slug}.md")
    except MalformedFragment as exc:
        return False, str(exc)
    missing = [lang for lang in TARGETS if not text.get(lang, "").strip()]
    if missing:
        return False, (
            f"{FRAGMENT_DIR}/{slug}.md has nothing under: {', '.join(sorted(missing))}. "
            "The project ships a pair, and half a pair is not an entry."
        )
    return True, f"{FRAGMENT_DIR}/{slug}.md carries {', '.join(sorted(text))}"


def collect(root: str) -> list[Fragment]:
    """Every fragment, slug order — so two assemblies of the same set agree."""
    base = os.path.join(root, FRAGMENT_DIR)
    if not os.path.isdir(base):
        return []
    out: list[Fragment] = []
    for name in sorted(os.listdir(base)):
        if not name.endswith(".md") or name.startswith("."):
            continue
        path = os.path.join(base, name)
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        if not raw.strip():
            raise MalformedFragment(f"{FRAGMENT_DIR}/{name} is empty.")
        out.append(Fragment(slug=name[:-3], path=path, text=parse(raw, f"{FRAGMENT_DIR}/{name}")))
    return out


def assemble(root: str, *, apply: bool = False) -> list[str]:
    """Fold every fragment into both changelogs and remove it. Returns what happened.

    Raises `MalformedFragment` BEFORE writing anything: a half-applied assembly would leave
    some fragments folded and others deleted with nothing to show for them.
    """
    fragments = collect(root)
    if not fragments:
        return ["no fragments to assemble"]

    written: dict[str, str] = {}
    for lang, target in TARGETS.items():
        path = os.path.join(root, target)
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                raw = fh.read()
        except OSError as exc:
            raise MalformedFragment(f"{target} could not be read: {exc}") from exc
        newline = "\r\n" if "\r\n" in raw else "\n"
        body = raw.replace("\r\n", "\n")
        if UNRELEASED not in body:
            raise MalformedFragment(f"{target} has no `{UNRELEASED}` heading to fold into.")
        at = body.index(UNRELEASED) + len(UNRELEASED)
        added = "\n\n".join(f.text[lang].strip() for f in fragments)
        body = body[:at] + "\n\n" + added + "\n\n" + body[at:].lstrip("\n")
        written[path] = body.replace("\n", newline) if newline == "\r\n" else body

    said = [f"{len(fragments)} fragment(s): {', '.join(f.slug for f in fragments)}"]
    if not apply:
        said.append("would fold into " + " and ".join(TARGETS.values()) + " (pass --apply)")
        return said
    for path, body in written.items():
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
    for fragment in fragments:
        os.remove(fragment.path)
    said.append("folded into " + " and ".join(TARGETS.values()) + "; fragments removed")
    return said


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
