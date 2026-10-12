#!/usr/bin/env python3
"""Stale-version + cross-link doc lint. Warning-only — exit 0 always.

Scans docs/, README.md, AGENTS.md, CONTRIBUTING.md, CLAUDE.md for:
  - stale version mentions (v1.0/v1.1/v1.2 outside CHANGELOG)
  - stale tool/skill/test counts
  - legacy framework name "frai"
Emits one line per finding, then a summary count.
"""

from __future__ import annotations

import os
import re
import sys

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

_STALE_PATTERNS = [
    (r"\bv1\.[012]\b", "stale-version"),
    (r"\b82 (?:MCP )?tools\b", "82-tools"),
    (r"\b80 (?:MCP )?tools\b", "80-tools"),
    (r"\b75 project\b", "75-project"),
    (r"\b73 project\b", "73-project"),
    (r"\b918 tests\b", "918-tests"),
    (r"\b1095 tests\b", "1095-tests"),
    (r"\b34 skills\b", "34-skills"),
    (r"\b13 (?:Claude (?:Code )?)?hooks\b", "13-hooks"),
    (r"\bfrai[- /]\b", "legacy-name-frai"),
]

_SCAN_PATHS = [
    "docs",
    "README.md",
    "README.ru.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "CLAUDE.md",
]
_EXCLUDE = {"CHANGELOG.md"}


def scan() -> int:
    findings = 0
    root = os.getcwd()
    for path in _SCAN_PATHS:
        full = os.path.join(root, path)
        if os.path.isfile(full):
            findings += _scan_file(full)
        elif os.path.isdir(full):
            for dirpath, _, files in os.walk(full):
                for f in files:
                    if not f.endswith(".md") or f in _EXCLUDE:
                        continue
                    findings += _scan_file(os.path.join(dirpath, f))
    if findings:
        print(
            f"[docs-lint] {findings} stale mention(s) found (warnings).",
            file=sys.stderr,
        )
    else:
        print("[docs-lint] clean.", file=sys.stderr)
    return 0


def _scan_file(path: str) -> int:
    rel = os.path.relpath(path, os.getcwd())
    count = 0
    try:
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, start=1):
                for pat, label in _STALE_PATTERNS:
                    if re.search(pat, line, re.IGNORECASE):
                        excerpt = line.strip()[:100]
                        print(f"WARN {rel}:{ln} [{label}] {excerpt}")
                        count += 1
    except OSError:
        pass
    return count


if __name__ == "__main__":
    sys.exit(scan())
