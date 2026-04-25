"""TAUSIK stack-decl validator (stdlib-only).

Validates parsed stack.json declarations against the shape documented in
stacks/_schema.json. Used by stack_registry.StackRegistry on load.

Honest schema: malformed entries return actionable error strings, never
silently skipped. Each error line names the source (e.g. file path),
the offending field, and the rule violated.
"""

from __future__ import annotations

import re
from typing import Any

# --- Public API -------------------------------------------------------------

VALID_DETECT_TYPES = frozenset({"exact", "glob", "dir-marker"})
VALID_GATE_SEVERITIES = frozenset({"warn", "block"})
VALID_GATE_TRIGGERS = frozenset({"task-done", "commit", "review"})

_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_EXT_RE = re.compile(r"^\.[a-z0-9.]+$")
_FILENAME_RE = re.compile(r"^[a-z0-9._-]+$")
_PATH_HINT_RE = re.compile(r"^/[^/].*/$")
_EXTENDS_RE = re.compile(r"^builtin:[a-z][a-z0-9_-]*$")
_GATE_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

_TOP_LEVEL_KEYS = frozenset(
    {
        "name",
        "version",
        "extends",
        "detect",
        "extensions",
        "filenames",
        "path_hints",
        "gates",
        "guide_path",
        "extensions_extra",
    }
)


def validate_decl(decl: Any, source: str = "<unknown>") -> list[str]:
    """Return list of validation errors (empty if valid).

    Each message is a single line: "<source>: <field>: <reason>".
    Caller decides whether to log warnings, skip the stack, or fail hard.
    """
    errors: list[str] = []
    prefix = f"{source}: "

    if not isinstance(decl, dict):
        errors.append(f"{prefix}root: must be a JSON object, got {type(decl).__name__}")
        return errors

    # name (required)
    name = decl.get("name")
    if name is None:
        errors.append(f"{prefix}'name' is required")
    elif not isinstance(name, str):
        errors.append(f"{prefix}'name' must be a string, got {type(name).__name__}")
    elif not _NAME_RE.match(name):
        errors.append(
            f"{prefix}'name' must match {_NAME_RE.pattern} (lowercase, "
            f"start with letter, alphanumeric/underscore/dash), got {name!r}"
        )

    # Reject unknown top-level keys (catches typos like 'detects' for 'detect').
    for k in decl:
        if k not in _TOP_LEVEL_KEYS:
            errors.append(
                f"{prefix}unknown top-level field {k!r}. "
                f"Allowed: {sorted(_TOP_LEVEL_KEYS)}"
            )

    # version
    if "version" in decl and not isinstance(decl["version"], str):
        errors.append(
            f"{prefix}'version' must be a string, got {type(decl['version']).__name__}"
        )

    # extends
    if "extends" in decl and decl["extends"] is not None:
        ext = decl["extends"]
        if not isinstance(ext, str):
            errors.append(
                f"{prefix}'extends' must be a string or null, got {type(ext).__name__}"
            )
        elif not _EXTENDS_RE.match(ext):
            errors.append(
                f"{prefix}'extends' must match 'builtin:NAME' pattern, got {ext!r}"
            )

    # detect
    errors.extend(_validate_detect(decl.get("detect"), prefix))

    # extensions
    errors.extend(
        _validate_str_list(decl.get("extensions"), "extensions", prefix, _EXT_RE)
    )
    # extensions_extra (same shape)
    errors.extend(
        _validate_str_list(
            decl.get("extensions_extra"), "extensions_extra", prefix, _EXT_RE
        )
    )

    # filenames
    errors.extend(
        _validate_str_list(decl.get("filenames"), "filenames", prefix, _FILENAME_RE)
    )

    # path_hints
    errors.extend(
        _validate_str_list(decl.get("path_hints"), "path_hints", prefix, _PATH_HINT_RE)
    )

    # gates
    errors.extend(_validate_gates(decl.get("gates"), prefix))

    # guide_path
    if "guide_path" in decl and not isinstance(decl["guide_path"], str):
        errors.append(
            f"{prefix}'guide_path' must be a string, got "
            f"{type(decl['guide_path']).__name__}"
        )

    return errors


# --- Internal helpers -------------------------------------------------------


def _validate_detect(detect: Any, prefix: str) -> list[str]:
    if detect is None:
        return []
    errors: list[str] = []
    if not isinstance(detect, list):
        return [f"{prefix}'detect' must be a list, got {type(detect).__name__}"]
    for i, entry in enumerate(detect):
        loc = f"detect[{i}]"
        if not isinstance(entry, dict):
            errors.append(
                f"{prefix}{loc}: must be an object, got {type(entry).__name__}"
            )
            continue
        # required: file, type
        if "file" not in entry:
            errors.append(f"{prefix}{loc}: 'file' is required")
        elif not isinstance(entry["file"], str) or not entry["file"]:
            errors.append(f"{prefix}{loc}.file: must be a non-empty string")
        if "type" not in entry:
            errors.append(f"{prefix}{loc}: 'type' is required")
        elif entry["type"] not in VALID_DETECT_TYPES:
            errors.append(
                f"{prefix}{loc}.type: must be one of "
                f"{sorted(VALID_DETECT_TYPES)}, got {entry['type']!r}"
            )
        # optional: keyword
        if "keyword" in entry and not isinstance(entry["keyword"], str):
            errors.append(
                f"{prefix}{loc}.keyword: must be a string, got "
                f"{type(entry['keyword']).__name__}"
            )
        # reject unknown fields
        for k in entry:
            if k not in {"file", "type", "keyword"}:
                errors.append(f"{prefix}{loc}: unknown field {k!r}")
    return errors


def _validate_str_list(
    value: Any, field: str, prefix: str, item_re: re.Pattern
) -> list[str]:
    if value is None:
        return []
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{prefix}{field!r} must be a list, got {type(value).__name__}"]
    seen: set[str] = set()
    for i, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(
                f"{prefix}{field}[{i}]: must be a string, got {type(item).__name__}"
            )
            continue
        if not item_re.match(item):
            errors.append(
                f"{prefix}{field}[{i}]: must match {item_re.pattern}, got {item!r}"
            )
        if item in seen:
            errors.append(f"{prefix}{field}[{i}]: duplicate entry {item!r}")
        seen.add(item)
    return errors


def _validate_gates(gates: Any, prefix: str) -> list[str]:
    if gates is None:
        return []
    errors: list[str] = []
    if not isinstance(gates, dict):
        return [f"{prefix}'gates' must be an object, got {type(gates).__name__}"]
    for gname, gcfg in gates.items():
        if not isinstance(gname, str) or not _GATE_NAME_RE.match(gname):
            errors.append(
                f"{prefix}gates: gate name must match {_GATE_NAME_RE.pattern}, "
                f"got {gname!r}"
            )
            continue
        # null = disable inherited gate; allowed.
        if gcfg is None:
            continue
        if not isinstance(gcfg, dict):
            errors.append(
                f"{prefix}gates.{gname}: must be an object or null, got "
                f"{type(gcfg).__name__}"
            )
            continue
        errors.extend(_validate_gate_cfg(gcfg, prefix, gname))
    return errors


def _validate_gate_cfg(gcfg: dict, prefix: str, gname: str) -> list[str]:
    errors: list[str] = []
    if "enabled" in gcfg and not isinstance(gcfg["enabled"], bool):
        errors.append(f"{prefix}gates.{gname}.enabled: must be bool")
    if "severity" in gcfg and gcfg["severity"] not in VALID_GATE_SEVERITIES:
        errors.append(
            f"{prefix}gates.{gname}.severity: must be one of "
            f"{sorted(VALID_GATE_SEVERITIES)}, got {gcfg['severity']!r}"
        )
    if "trigger" in gcfg:
        trig = gcfg["trigger"]
        if not isinstance(trig, list):
            errors.append(f"{prefix}gates.{gname}.trigger: must be a list")
        else:
            for i, t in enumerate(trig):
                if t not in VALID_GATE_TRIGGERS:
                    errors.append(
                        f"{prefix}gates.{gname}.trigger[{i}]: must be one of "
                        f"{sorted(VALID_GATE_TRIGGERS)}, got {t!r}"
                    )
    if "command" in gcfg and gcfg["command"] is not None:
        if not isinstance(gcfg["command"], str):
            errors.append(f"{prefix}gates.{gname}.command: must be a string or null")
    if "description" in gcfg and not isinstance(gcfg["description"], str):
        errors.append(f"{prefix}gates.{gname}.description: must be a string")
    for list_field in ("file_extensions", "stacks"):
        if list_field in gcfg:
            v = gcfg[list_field]
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                errors.append(
                    f"{prefix}gates.{gname}.{list_field}: must be a list of strings"
                )
    for int_field in ("timeout", "max_lines"):
        if int_field in gcfg:
            v = gcfg[int_field]
            if not isinstance(v, int) or isinstance(v, bool) or v < 1:
                errors.append(
                    f"{prefix}gates.{gname}.{int_field}: must be a positive integer"
                )
    return errors


# --- Smoke check (run as: python -m stack_schema) --------------------------

if __name__ == "__main__":
    cases = [
        ({}, "missing-name", True),
        ({"name": "py", "detect": "nope"}, "detect-not-list", True),
        (
            {"name": "py", "detect": [{"file": "x", "type": "regex"}]},
            "bad-detect-type",
            True,
        ),
        ({"name": "py", "extensions": [".py", ".py"]}, "duplicate-ext", True),
        ({"name": "py"}, "minimal-valid", False),
        (
            {
                "name": "go",
                "version": "1",
                "detect": [{"file": "go.mod", "type": "exact"}],
                "extensions": [".go"],
                "gates": {"go-vet": {"enabled": True, "severity": "block"}},
            },
            "full-valid",
            False,
        ),
    ]
    for decl, label, expect_errors in cases:
        errs = validate_decl(decl, source=f"smoke[{label}]")
        ok = bool(errs) == expect_errors
        print(f"[{'OK' if ok else 'FAIL'}] {label}: {len(errs)} error(s)")
        for e in errs:
            print(f"  - {e}")
