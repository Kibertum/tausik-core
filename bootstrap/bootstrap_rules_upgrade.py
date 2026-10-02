"""Safe, idempotent upgrades for user-owned agent instruction files."""

from __future__ import annotations


_DYNAMIC_START = b"<!-- DYNAMIC:START -->"

TEST_DISCIPLINE = """## Test discipline

File changes alone do not require tests. Reuse behavioral coverage; remove redundant existence, wording/count, import-only and mock-only checks. Preserve security and public contracts. Details: `docs/en/testing-principles.md`.
"""

TEST_DISCIPLINE_MARKER = "## Test discipline"

_LEGACY_ANSWER_SHAPE_BODY = """- Responses are in the user's language.
- SHAPE, empty parts omitted: done → verified by → left → your call.
- KEEP BYTE-EXACT: code, shell commands, tool output, file paths, error messages. KEEP FULL PROSE: acceptance-criteria evidence, decisions, SPEC/ADAPT, task logs, handoffs.
- EXCEPTIONS: explanation asked; destructive action; three failed debugging turns → state the assumption, ask; ambiguity → one question; the rule would delete the answer itself.
- Steps numbered, one action each, the last doable in two minutes; five items per group unless completeness needs more. One tangent, once, at the end. Estimates in minutes.
- PRE-SEND: delete announcements, closing recaps, side branches, hedges; first line = next action, last line = current state.
"""


def markdown_contains_any(path: str, markers: tuple[str, ...]) -> bool:
    """Whether a UTF-8 rules file already carries an equivalent contract."""
    try:
        with open(path, encoding="utf-8") as stream:
            text = stream.read()
    except (OSError, UnicodeError):
        return False
    return any(marker in text for marker in markers)


def reconcile_markdown_block(path: str, marker: str, block: str) -> bool:
    """Insert ``block`` once without rewriting any existing byte.

    A managed block lands before TAUSIK's dynamic state when that marker exists,
    otherwise at EOF. Non-UTF-8 files are left untouched because preserving text
    the framework cannot decode would be a false guarantee.
    """
    try:
        with open(path, "rb") as stream:
            raw = stream.read()
        raw.decode("utf-8")
        if marker.encode("utf-8") in raw:
            return False
        newline = b"\r\n" if b"\r\n" in raw else b"\n"
        encoded = block.replace("\n", newline.decode()).encode("utf-8")
        insert_at = raw.find(_DYNAMIC_START)
        if insert_at >= 0:
            before, after = raw[:insert_at], raw[insert_at:]
            separator = _separator(before, newline)
            updated = before + separator + encoded + newline * 2 + after
        else:
            updated = raw + _separator(raw, newline) + encoded + newline
        with open(path, "wb") as stream:
            stream.write(updated)
        return True
    except (OSError, UnicodeError):
        return False


def reconcile_answer_shape(path: str, marker: str, block: str) -> str | None:
    """Add the answer shape or replace the exact legacy canonical body.

    A file with a customized block is user-owned and remains byte-identical.
    """
    try:
        with open(path, "rb") as stream:
            raw = stream.read()
        raw.decode("utf-8")
        newline = b"\r\n" if b"\r\n" in raw else b"\n"
        current_body = block.split("\n\n", 1)[1].replace("\n", newline.decode()).encode()
        legacy_body = _LEGACY_ANSWER_SHAPE_BODY.replace("\n", newline.decode()).encode()
        if current_body in raw:
            return None
        if legacy_body in raw:
            with open(path, "wb") as stream:
                stream.write(raw.replace(legacy_body, current_body, 1))
            return "upgraded"
    except (OSError, UnicodeError, IndexError):
        return None
    if reconcile_markdown_block(path, marker, block):
        return "added"
    return None


def _separator(before: bytes, newline: bytes) -> bytes:
    if not before or before.endswith(newline * 2):
        return b""
    if before.endswith(newline):
        return newline
    return newline * 2
