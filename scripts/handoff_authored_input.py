"""Load and validate authored session-handoff JSON for CLI and MCP.

Positional JSON on Windows/PowerShell splits on spaces into multiple argv
entries (`unrecognized arguments`). Callers should prefer `--json-file` or
stdin. This module is the single schema: invalid input never reaches
`session_handoff`, so a partial handoff cannot be stored.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO


class AuthoredHandoffInputError(ValueError):
    """Structured refusal before any handoff write."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "error": "authored_handoff_input"}


def validate_authored(data: Any) -> dict[str, Any]:
    """Return a dict suitable for `merge_authored`, or raise AuthoredHandoffInputError."""
    if data is None:
        raise AuthoredHandoffInputError("EMPTY", "authored handoff payload is null")
    if not isinstance(data, dict):
        raise AuthoredHandoffInputError(
            "NOT_OBJECT",
            f"authored handoff must be a JSON object, got {type(data).__name__}",
        )
    out = dict(data)
    if "next_steps" in out and not _is_str_list(out["next_steps"]):
        raise AuthoredHandoffInputError(
            "BAD_NEXT_STEPS", "next_steps must be an array of strings when present"
        )
    if "warnings" in out and not _is_str_list(out["warnings"]):
        raise AuthoredHandoffInputError(
            "BAD_WARNINGS", "warnings must be an array of strings when present"
        )
    if "in_progress" in out:
        items = out["in_progress"]
        if not isinstance(items, list):
            raise AuthoredHandoffInputError(
                "BAD_IN_PROGRESS", "in_progress must be an array when present"
            )
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                raise AuthoredHandoffInputError(
                    "BAD_IN_PROGRESS_ITEM",
                    f"in_progress[{i}] must be an object with slug and optional state",
                )
            if "slug" in item and not isinstance(item["slug"], str):
                raise AuthoredHandoffInputError(
                    "BAD_IN_PROGRESS_SLUG", f"in_progress[{i}].slug must be a string"
                )
            if "state" in item and not isinstance(item["state"], str):
                raise AuthoredHandoffInputError(
                    "BAD_IN_PROGRESS_STATE", f"in_progress[{i}].state must be a string"
                )
    return out


def parse_authored_text(raw: str, *, source: str) -> dict[str, Any]:
    """Parse UTF-8 JSON text from a named source, then validate."""
    if raw is None:
        raise AuthoredHandoffInputError("EMPTY", f"{source}: empty payload")
    text = raw.strip("\ufeff")
    if not text.strip():
        raise AuthoredHandoffInputError("EMPTY", f"{source}: empty payload")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuthoredHandoffInputError(
            "INVALID_JSON",
            f"{source}: {exc.msg} at line {exc.lineno} column {exc.colno}",
        ) from exc
    return validate_authored(data)


def load_authored(
    *,
    positional: str | None = None,
    json_file: str | None = None,
    json_stdin: bool = False,
    stdin: TextIO | None = None,
) -> dict[str, Any] | None:
    """Load authored fields from exactly one source, or None when none given.

    Sources: positional string, `--json-file`, or stdin (`--json-stdin` or
    positional `-`). More than one source is a conflict.
    """
    use_stdin = bool(json_stdin) or (positional == "-")
    pos = None if positional in (None, "-") else positional
    sources = [
        name
        for name, present in (
            ("positional", bool(pos)),
            ("json-file", bool(json_file)),
            ("stdin", use_stdin),
        )
        if present
    ]
    if len(sources) > 1:
        raise AuthoredHandoffInputError(
            "CONFLICT",
            f"use only one of positional JSON, --json-file, or stdin (got: {', '.join(sources)})",
        )
    if not sources:
        return None
    if json_file:
        path = Path(json_file)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise AuthoredHandoffInputError("FILE_READ", f"--json-file {json_file}: {exc}") from exc
        return parse_authored_text(raw, source=f"--json-file {json_file}")
    if use_stdin:
        stream = stdin if stdin is not None else sys.stdin
        raw = stream.read()
        return parse_authored_text(raw, source="stdin")
    assert pos is not None
    return parse_authored_text(pos, source="positional")


def load_from_cli_args(args: Any, *, stdin: TextIO | None = None) -> dict[str, Any] | None:
    """Adapter for argparse Namespace from `session handoff`."""
    return load_authored(
        positional=getattr(args, "json_data", None),
        json_file=getattr(args, "json_file", None),
        json_stdin=bool(getattr(args, "json_stdin", False)),
        stdin=stdin,
    )


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)
