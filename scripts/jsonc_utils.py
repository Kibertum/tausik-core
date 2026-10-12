"""Shared JSONC reader — the ONE parser for configs that tolerate comments.

Kilo writes ``kilo.jsonc`` (comments allowed); TAUSIK writes plain JSON into
the same files. Both the doctor and the model-detection provider need to read
such configs, and a second copy of comment-stripping logic is exactly the kind
of oracle drift this framework refuses (convention #266): when the fallback
rules change, they change in ONE place.

Best-effort JSONC stripping: Kilo tolerates ``//`` and ``/* */`` comments —
including comments AFTER a value on the same line, the common hand-edited
style — plus trailing commas; ``json.loads`` does not. Strict parsing is tried
FIRST, so a plain-JSON file never touches the fallback. The fallback is a
string-aware scanner, not a regex: a regex that eats ``//`` anywhere would
mangle ``"https://..."`` inside a string value.
"""

from __future__ import annotations

import json
import re

_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def _strip_comments(raw: str) -> str:
    """Remove // and /* */ comments outside string literals, character-wise."""
    out: list[str] = []
    i = 0
    n = len(raw)
    in_string = False
    while i < n:
        ch = raw[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(raw[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and raw[i + 1] == "/":
            while i < n and raw[i] != "\n":
                i += 1
            continue  # keep the newline itself
        if ch == "/" and i + 1 < n and raw[i + 1] == "*":
            i += 2
            while i + 1 < n and not (raw[i] == "*" and raw[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def load_jsonc(path: str) -> dict:
    """Parse a (possibly JSONC) config file. Raises ValueError if unparseable."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        stripped = _TRAILING_COMMA.sub(r"\1", _strip_comments(raw))
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(str(e)) from e
    if not isinstance(data, dict):
        raise ValueError("top-level value is not a JSON object")
    return data
