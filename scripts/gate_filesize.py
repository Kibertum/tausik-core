"""TAUSIK filesize gate — line-cap enforcement with exempt dirs/basenames.

Extracted from gate_runner.py for filesize compliance (gate_runner sat exactly
at the 400-line cap, so any addition broke it). gate_runner re-exports
``count_lines`` and ``run_filesize_gate`` so existing imports (tests, the
run_gates dispatch) keep working unchanged.
"""

from __future__ import annotations

import os


def count_lines(filepath: str) -> int:
    """Count lines in a file."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


_FILESIZE_EXEMPT_DIRS = (
    "tests/",
    "harness/claude/mcp/",
    "harness/cursor/mcp/",
    "harness/qwen/mcp/",
    ".claude/mcp/",
    # Common exempt dirs for source materials, ADR markdowns, agent configs.
    "docs/content/",
    "docs/architecture/",
    "backend/configs/",
    # Research dumps grow large by design (convention #122) — exempt in the
    # committed gate so a fresh clone / CI does not block on them (the per-project
    # .tausik/config.json exempt is gitignored and not present on a fresh clone).
    "docs/en/research/",
    "docs/ru/research/",
)

# Reference docs that grow by design (one entry per command/release) — exempt
# from the line cap in the committed gate, same rationale as the research dumps
# above: a fresh clone / CI must not block on them, and the per-project
# .tausik/config.json exempt is gitignored.
_FILESIZE_EXEMPT_BASENAMES = frozenset(
    {
        "CHANGELOG.md",
        "CHANGELOG.ru.md",
        "cli.md",  # docs/{en,ru}/cli.md — full CLI command reference
    }
)


def _normalize_path(p: str) -> str:
    """Canonicalize path for matching: forward slashes, strip leading './'."""
    n = os.path.normpath(p).replace("\\", "/")
    if n.startswith("./"):
        n = n[2:]
    return n


def run_filesize_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Check file sizes against max_lines threshold.

    Exempt: tests, MCP handlers (dispatchers, not creative logic).
    Per-file exempts via gate.exempt_files: entries with '/' match by exact
    path, bare names match by basename (covers a file anywhere in tree).
    """
    max_lines = gate.get("max_lines", 400)
    exempt_paths: set[str] = set()
    exempt_basenames: set[str] = set()
    for entry in gate.get("exempt_files") or []:
        norm = entry.replace("\\", "/")
        if "/" in norm:
            exempt_paths.add(_normalize_path(norm))
        else:
            exempt_basenames.add(norm)

    violations = []
    for f in files:
        if not os.path.isfile(f):
            continue
        normalized = f.replace("\\", "/")
        if any(d in normalized for d in _FILESIZE_EXEMPT_DIRS):
            continue
        canon = _normalize_path(f)
        basename = os.path.basename(canon)
        if canon in exempt_paths or basename in exempt_basenames:
            continue
        if basename in _FILESIZE_EXEMPT_BASENAMES:
            continue
        lines = count_lines(f)
        if lines > max_lines:
            violations.append(f"  {f}: {lines} lines (max {max_lines})")
    if violations:
        return False, "Files exceeding line limit:\n" + "\n".join(violations)
    return True, "All files within line limit."
