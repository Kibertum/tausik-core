"""`tausik aidd validate` — drift between conventions.md claims and repo state.

Parses machine-checkable claims from the conventions.md `## Code` section
(language/version pin, lint/format tool, testing framework, max file-size
limit) and compares each against the actual repo. Reports ok / drift /
unverifiable per claim. Exit 1 on hard drift, exit 2 on missing
conventions.md, exit 0 otherwise. Stdlib-only, no LLM call; an unparseable
claim is reported unverifiable and never crashes the run.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Callable

from project_cli_aidd import _read
from project_cli_aidd_autogen import (
    _DENY_DIRS,
    _EXT_LANG,
    _detect_test_framework,
    tomllib,
)

_CLAIM_ORDER: tuple[str, ...] = ("lang_version", "lint_tool", "test_framework", "max_filesize")

_CLAIM_LABELS: dict[str, str] = {
    "lang_version": "Language/version pin",
    "lint_tool": "Lint/format tool",
    "test_framework": "Testing framework",
    "max_filesize": "Max file size",
}

_LINT_TOOLS: tuple[str, ...] = (
    "ruff",
    "black",
    "flake8",
    "isort",
    "mypy",
    "pylint",
    "eslint",
    "prettier",
)

# Tool → config filenames that prove the tool is wired up (besides pyproject).
_TOOL_CONFIG_FILES: dict[str, tuple[str, ...]] = {
    "ruff": ("ruff.toml", ".ruff.toml"),
    "flake8": (".flake8",),
    "isort": (".isort.cfg",),
    "mypy": ("mypy.ini", ".mypy.ini"),
    "pylint": (".pylintrc", "pylintrc"),
    "eslint": (".eslintrc", ".eslintrc.json", ".eslintrc.js", "eslint.config.js"),
    "prettier": (".prettierrc", ".prettierrc.json", "prettier.config.js"),
}


def _extract_code_bullets(text: str) -> list[str]:
    """Return bullet lines (label text only) under the first `## Code` section."""
    bullets: list[str] = []
    in_code = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            # Exact match only — avoid '## Code of conduct' / '## Codebase'.
            in_code = line[3:].strip().lower() == "code"
            continue
        if in_code and line.startswith(("-", "*")):
            bullets.append(line.lstrip("-* ").strip())
    return bullets


def _parse_claims(text: str) -> dict[str, str]:
    """Map each recognized `## Code` bullet to a claim type → value string."""
    claims: dict[str, str] = {}
    for bullet in _extract_code_bullets(text):
        if ":" not in bullet:
            continue
        label, _, value = bullet.partition(":")
        label_l = label.strip().lower()
        value = value.strip()
        if "version" in label_l or "language" in label_l:
            claims["lang_version"] = value
        elif "lint" in label_l or "format" in label_l:
            claims["lint_tool"] = value
        elif "test" in label_l:
            claims["test_framework"] = value
        elif "file size" in label_l or "filesize" in label_l or "cyclomatic" in label_l:
            claims["max_filesize"] = value
    return claims


def _load_pyproject(root: str) -> dict | None:
    pyproject = os.path.join(root, "pyproject.toml")
    if tomllib is None or not os.path.isfile(pyproject):
        return None
    try:
        with open(pyproject, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _collect_pyproject_deps(data: dict) -> list[str]:
    project = data.get("project") or {}
    deps = list(project.get("dependencies") or [])
    for group in (project.get("optional-dependencies") or {}).values():
        deps.extend(group or [])
    for group in (data.get("dependency-groups") or {}).values():
        deps.extend(group or [])
    return [str(d).lower() for d in deps]


def _minor_version(text: str) -> tuple[int, int] | None:
    """First (major, minor) version pair in a string, else None."""
    m = re.search(r"(\d+)\.(\d+)", text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _verify_lang_version(root: str, value: str) -> tuple[str, str]:
    if not value:
        return "unverifiable", "claim is blank"
    data = _load_pyproject(root)
    req = ((data or {}).get("project") or {}).get("requires-python")
    if "python" not in value.lower():
        return "unverifiable", f"non-Python claim '{value}' cannot be version-checked"
    if not req:
        return "unverifiable", f"claim '{value}' but no requires-python in pyproject.toml"
    claim_ver = _minor_version(value)
    req_ver = _minor_version(req)
    if claim_ver is None:
        return "unverifiable", f"requires-python='{req}', claim '{value}' has no version number"
    if req_ver is None:
        return "unverifiable", f"claim '{value}' but requires-python='{req}' has no version number"
    # Operator-aware comparison:
    #  - req is a FLOOR ('>=3.11','~=3.11','>') and the claim is an EXACT pin
    #    (e.g. 'Python 3.13', no '+') → ok when the pin satisfies the floor
    #    (same major, >= floor): developing on 3.13 while supporting 3.11+ is fine.
    #  - both are floors (claim 'X+'/'>=' AND req floor) → the DECLARED minimums
    #    must agree (a doc floor of 3.11 vs a pyproject floor of 3.9 is real drift).
    #  - req is exact ('==') → exact match required.
    req_op = re.search(r"(>=|<=|~=|==|>|<)", req)
    req_is_floor = req_op is not None and req_op.group(1) in {">=", "~=", ">"}
    claim_is_floor = bool(re.search(r"(\+|>=|~=|>)", value))
    if req_is_floor and not claim_is_floor:
        ok = claim_ver[0] == req_ver[0] and claim_ver >= req_ver
    else:
        ok = claim_ver == req_ver
    if ok:
        return "ok", f"requires-python '{req}' satisfies claim '{value}'"
    return "drift", f"claim '{value}' but pyproject requires-python='{req}'"


def _dep_names_tool(dep: str, tool: str) -> bool:
    """True if a dependency spec names exactly `tool` (not 'flake8-bugbear')."""
    return bool(re.match(re.escape(tool) + r"($|[=<>!~;\[\s])", dep))


def _package_json_has_tool(root: str, tool: str) -> bool:
    pkg = os.path.join(root, "package.json")
    if not os.path.isfile(pkg):
        return False
    try:
        with open(pkg, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    deps = {**(data.get("devDependencies") or {}), **(data.get("dependencies") or {})}
    return tool in {str(k).lower() for k in deps}


def _tool_present(root: str, tool: str, data: dict | None) -> bool:
    for cf in _TOOL_CONFIG_FILES.get(tool, ()):
        if os.path.isfile(os.path.join(root, cf)):
            return True
    if data is not None:
        if tool in (data.get("tool") or {}):
            return True
        if any(_dep_names_tool(d, tool) for d in _collect_pyproject_deps(data)):
            return True
    # Flat requirement/config files: tool name at a line start (avoids comment /
    # substring false-positives like 'flake8-bugbear' matching 'flake8').
    line_re = re.compile(r"(?mi)^\s*" + re.escape(tool) + r"(?=$|[=<>!~;\[\s])")
    for fname in ("requirements.txt", "requirements-dev.txt", "setup.cfg", "tox.ini"):
        path = os.path.join(root, fname)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    if line_re.search(f.read()):
                        return True
            except OSError:
                pass
    return _package_json_has_tool(root, tool)


def _verify_lint_tool(root: str, value: str) -> tuple[str, str]:
    if not value:
        return "unverifiable", "claim is blank"
    low = value.lower()
    claimed = [t for t in _LINT_TOOLS if re.search(r"\b" + re.escape(t) + r"\b", low)]
    if not claimed:
        return "unverifiable", f"no recognized tool in claim '{value}'"
    data = _load_pyproject(root)
    missing = [t for t in claimed if not _tool_present(root, t, data)]
    if missing:
        return "drift", f"claimed {claimed} but not configured: {missing}"
    return "ok", f"configured: {claimed}"


def _verify_test_framework(root: str, value: str) -> tuple[str, str]:
    if not value:
        return "unverifiable", "claim is blank"
    detected = _detect_test_framework(root)
    if detected is None:
        return "unverifiable", f"claim '{value}' but no framework detected in repo"
    # Word-boundary, not substring: detected 'ava' must NOT match claim 'java...'.
    if re.search(r"\b" + re.escape(detected) + r"\b", value.lower()):
        return "ok", f"detected '{detected}' matches claim"
    return "drift", f"claim '{value}' but repo uses '{detected}'"


def _files_over(root: str, limit: int, max_files: int = 4000) -> tuple[list[str], bool]:
    """Return (offenders, truncated). `truncated` is True if the walk hit its
    file cap before finishing — the caller must then NOT claim 'ok' (it didn't
    actually confirm every file)."""
    offenders: list[str] = []
    seen = 0  # count ALL visited files toward the circuit breaker, not just source
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in _DENY_DIRS]
        for fn in filenames:
            if seen >= max_files:
                return offenders, True
            seen += 1
            if os.path.splitext(fn)[1].lower() not in _EXT_LANG:
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    over = False
                    n = 0
                    for _ in f:
                        n += 1
                        if n > limit:  # early exit once over the cap
                            over = True
                            break
            except OSError:
                continue
            if over:
                offenders.append(os.path.relpath(full, root).replace("\\", "/"))
    return offenders, False


def _verify_max_filesize(root: str, value: str) -> tuple[str, str]:
    if not value:
        return "unverifiable", "claim is blank"
    m = re.search(r"(\d+)", value)
    if not m:
        return "unverifiable", f"no line count in claim '{value}'"
    limit = int(m.group(1))
    offenders, truncated = _files_over(root, limit)
    if not offenders:
        if truncated:
            return "unverifiable", f"file walk hit its cap before confirming <={limit} lines"
        return "ok", f"no source file exceeds {limit} lines"
    shown = ", ".join(offenders[:3])
    more = "" if len(offenders) <= 3 else f" (+{len(offenders) - 3} more)"
    return "drift", f"limit {limit} lines, exceeded by: {shown}{more}"


_VERIFIERS = {
    "lang_version": _verify_lang_version,
    "lint_tool": _verify_lint_tool,
    "test_framework": _verify_test_framework,
    "max_filesize": _verify_max_filesize,
}


def cmd_aidd_validate(*, root: str | None = None, log: Callable[[str], None] | None = None) -> int:
    """CLI entry for `tausik aidd validate`. Returns a POSIX exit code."""
    out = log or (lambda msg: print(msg))
    root = root or os.getcwd()
    path = os.path.join(root, "conventions.md")
    if not os.path.isfile(path):
        print("Error: conventions.md not found in project root", file=sys.stderr)
        return 2
    try:
        text = _read(path)
    except OSError as e:
        print(f"Error: cannot read conventions.md: {e}", file=sys.stderr)
        return 2
    claims = _parse_claims(text)
    n_ok = n_drift = n_unver = 0
    for key in _CLAIM_ORDER:
        value = claims.get(key)
        if value is None:
            status, detail = "unverifiable", "claim absent from conventions.md ## Code"
        else:
            try:
                status, detail = _VERIFIERS[key](root, value)
            except Exception as e:  # noqa: BLE001 - a bad claim must never crash the run
                status, detail = "unverifiable", f"check errored: {e}"
        out(f"[{status}] {_CLAIM_LABELS[key]}: {detail}")
        if status == "drift":
            n_drift += 1
        elif status == "ok":
            n_ok += 1
        else:
            n_unver += 1
    out(f"Summary: {n_ok} ok, {n_drift} drift, {n_unver} unverifiable.")
    return 1 if n_drift else 0
