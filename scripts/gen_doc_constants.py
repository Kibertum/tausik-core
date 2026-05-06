"""Generate `docs/_generated/constants.json` from pyproject + MCP tool counts.

Usage:
  python scripts/gen_doc_constants.py                      # write / update file
  python scripts/gen_doc_constants.py --check              # exit 1 on drift (constants.json + cross-file refs)
  python scripts/gen_doc_constants.py --check --skip-cross-files
                                                            # exit 1 on constants.json drift only (legacy)
  python scripts/gen_doc_constants.py --check --skip-mcp-counts
                                                            # exit 1 on constants + version refs only (skip MCP counts)

Also available as: ``tausik doc constants [--check]``.

Cross-file scan walks README.md, README.ru.md, AGENTS.md, CLAUDE.md,
docs/en/architecture.md, docs/ru/architecture.md, docs/en/mcp.md, docs/ru/mcp.md
and verifies (a) every ``vX.Y`` / ``vX.Y.Z`` version ref against
``constants.json["tausik_version"]`` and (b) common MCP tool-count phrasings
(``**N tools**``, ``N project tools``, ``N brain tools``, ``(N project + M brain``,
```tausik-brain`, N tools``) against ``constants.json``
(``mcp_project_tools`` / ``mcp_brain_tools`` / ``mcp_main_tools``). All scans
strip fenced code blocks first to avoid false positives in examples.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from mcp_tool_counts import mcp_counts_flat
from pytest_test_count import count_tests

_VERSION_RE = re.compile(r"\bv(\d+)\.(\d+)(?:\.(\d+))?(?:\.x)?\b")
_FENCED_BLOCK_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

CROSS_FILE_SCAN_TARGETS: tuple[str, ...] = (
    "README.md",
    "README.ru.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/en/architecture.md",
    "docs/ru/architecture.md",
    "docs/en/mcp.md",
    "docs/ru/mcp.md",
)

# RU/EN word for "tool" in MCP-count contexts. Matches singular + plural genitive
# forms: tools, tool, инструмент, инструмента, инструментов.
_TOOL_WORD = r"(?:tools?|инструмент(?:а|ов)?)"

# MCP tool-count patterns. Each entry is (compiled regex, constants_key, label).
# The capture group is a single integer compared against constants.json[key].
# Patterns are ordered specific-first so context-rich matches (brain header)
# fire before generic ones (`X project tools`).
_MCP_COUNT_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    # `tausik-brain`, N tools — brain server header, e.g. "## Shared Brain (`tausik-brain`, 7 tools)"
    (
        re.compile(rf"`tausik-brain`[^)]*?,\s*(\d+)\s+{_TOOL_WORD}", re.IGNORECASE),
        "mcp_brain_tools",
        "tausik-brain server header",
    ),
    # **N tools** / **N MCP tools** / **N MCP-инструментов** — markdown bold main count
    (
        re.compile(rf"\*\*(\d+)\s+(?:MCP[-\s]+)?{_TOOL_WORD}\*\*", re.IGNORECASE),
        "mcp_main_tools",
        "main count (bold)",
    ),
    # N project tools — explicit project count, e.g. "93 project tools"
    (
        re.compile(rf"\b(\d+)\s+project\s+{_TOOL_WORD}\b", re.IGNORECASE),
        "mcp_project_tools",
        "project count",
    ),
    # N brain tools — explicit brain count, e.g. "7 brain tools"
    (
        re.compile(rf"\b(\d+)\s+brain\s+{_TOOL_WORD}\b", re.IGNORECASE),
        "mcp_brain_tools",
        "brain count",
    ),
)

# Pair pattern: "(N project + M brain ...)" — both groups checked independently.
_MCP_COUNT_PAIR_PATTERN: tuple[re.Pattern[str], tuple[str, str], str] = (
    re.compile(r"\((\d+)\s+project\s*\+\s*(\d+)\s+brain", re.IGNORECASE),
    ("mcp_project_tools", "mcp_brain_tools"),
    "project+brain pair",
)

# Test-count patterns. Each entry is (compiled regex, label). The capture
# group is a single integer compared against constants.json["test_count"].
# Patterns are deliberately narrow to avoid false positives on illustrative
# numbers like "Never add 5 tests where one parametrized test covers".
_TEST_COUNT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # "pytest suite (N tests)"
    (re.compile(r"pytest\s+suite\s+\((\d+)\s+tests?\)", re.IGNORECASE), "pytest suite count"),
    # Badge URL: "tests-2590%20passed-brightgreen"
    (re.compile(r"tests-(\d+)%20passed", re.IGNORECASE), "badge URL count"),
    # Badge alt-text: "[![2590 tests](...)]"
    (re.compile(r"!\[(\d+)\s+tests?\]"), "badge label count"),
    # Markdown bold: "**N tests**" (used in changelogs / release notes)
    (re.compile(r"\*\*(\d+)\s+tests?\*\*"), "bold tests count"),
)


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` (default: cwd) for ``pyproject.toml``."""
    here = (start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / "pyproject.toml").is_file():
            return p
    print("Error: pyproject.toml not found — run from TAUSIK repo root.", file=sys.stderr)
    raise SystemExit(2)


def read_project_version(repo_root: Path) -> str:
    try:
        import tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]
    raw = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    if tomllib is not None:
        data = tomllib.loads(raw)
        return str(data["project"]["version"])
    # Fallback: regex if tomllib unavailable (should not happen on 3.11+)
    import re as _re

    m = _re.search(r'(?m)^version\s*=\s*"([^"]+)"', raw)
    if not m:
        raise ValueError("Could not parse version from pyproject.toml")
    return m.group(1)


def build_constants_doc(repo_root: Path) -> dict[str, object]:
    """Canonical payload written to ``constants.json``.

    ``test_count`` is the FULL suite size (no marker filter) measured via
    ``pytest --collect-only``; if collection fails the previous on-disk
    value is preserved so a transient pytest error doesn't poison the
    constants payload.
    """
    payload: dict[str, object] = {
        "schema_version": 1,
        "tausik_version": read_project_version(repo_root),
    }
    counts = mcp_counts_flat(repo_root)
    payload.update(counts)
    try:
        payload["test_count"] = count_tests(repo_root)
    except (ValueError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        # Preserve prior value rather than crash; surfaced in --check via
        # constants drift if the on-disk value diverges from a future re-run.
        on_disk_path = output_json_path(repo_root)
        if on_disk_path.is_file():
            try:
                prior = json.loads(on_disk_path.read_text(encoding="utf-8"))
                if isinstance(prior.get("test_count"), int):
                    payload["test_count"] = prior["test_count"]
            except (OSError, json.JSONDecodeError):
                pass
        if "test_count" not in payload:
            print(
                f"Warning: test_count omitted — pytest collection failed: {e}",
                file=sys.stderr,
            )
    return payload


def output_json_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "_generated" / "constants.json"


def _strip_fenced_blocks(text: str) -> str:
    """Replace fenced code blocks with same-line-count whitespace.

    Preserves line numbers in the returned text so matches outside fences
    can be reported with their original line number.
    """

    def _repl(m: re.Match[str]) -> str:
        return "\n" * m.group().count("\n")

    return _FENCED_BLOCK_RE.sub(_repl, text)


def _version_matches(major: int, minor: int, patch: int | None, expected: str) -> bool:
    """``patch`` is None for ``vX.Y`` refs — match major+minor only in that case."""
    parts = expected.split(".")
    exp_major = int(parts[0])
    exp_minor = int(parts[1]) if len(parts) > 1 else 0
    exp_patch = int(parts[2]) if len(parts) > 2 else 0
    if patch is None:
        return major == exp_major and minor == exp_minor
    return major == exp_major and minor == exp_minor and patch == exp_patch


_FOREIGN_VERSION_PREFIXES: tuple[str, ...] = ("SENAR", "Python", "OWASP")


def _is_foreign_version(text: str, match_start: int) -> bool:
    """True if the version ref belongs to another product (SENAR / Python / etc.).

    Looks 24 chars back from ``match_start`` for any of
    :data:`_FOREIGN_VERSION_PREFIXES` — these are products with independent
    version timelines that must not be checked against TAUSIK's.
    """
    window = text[max(0, match_start - 24) : match_start]
    return any(prefix in window for prefix in _FOREIGN_VERSION_PREFIXES)


def scan_version_refs(repo_root: Path, expected_version: str) -> list[str]:
    """Return drift messages for cross-file version refs.

    Walks :data:`CROSS_FILE_SCAN_TARGETS`, strips fenced code blocks, and
    flags every ``vX.Y`` / ``vX.Y.Z`` occurrence whose major.minor (and
    patch, if present) does not match ``expected_version``. Refs preceded
    by a foreign-version prefix (SENAR / Python / OWASP) are skipped —
    those products version independently.
    """
    messages: list[str] = []
    for rel in CROSS_FILE_SCAN_TARGETS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))
        for m in _VERSION_RE.finditer(text):
            if _is_foreign_version(text, m.start()):
                continue
            major = int(m.group(1))
            minor = int(m.group(2))
            patch = int(m.group(3)) if m.group(3) else None
            if _version_matches(major, minor, patch, expected_version):
                continue
            line_no = text[: m.start()].count("\n") + 1
            messages.append(
                f"{rel}:{line_no}: version ref '{m.group(0)}' "
                f"(major.minor={major}.{minor}) does not match "
                f"constants.json tausik_version={expected_version!r}"
            )
    return messages


def scan_mcp_tool_counts(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return drift messages for cross-file MCP tool-count refs.

    Walks :data:`CROSS_FILE_SCAN_TARGETS`, strips fenced code blocks, and flags
    every ``**N tools**`` / ``N project tools`` / ``N brain tools`` /
    ``(N project + M brain`` / ```tausik-brain`, N tools`` whose captured int
    does not match the corresponding constants.json key.

    Patterns are deliberately specific-context (require "project"/"brain"/
    backtick-wrapped server name nearby) to avoid noise on generic phrases like
    "200 tool calls" or "Should have 26+ tools".
    """
    messages: list[str] = []
    for rel in CROSS_FILE_SCAN_TARGETS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))

        for pattern, key, label in _MCP_COUNT_PATTERNS:
            expected = payload.get(key)
            if not isinstance(expected, int):
                continue
            for m in pattern.finditer(text):
                found = int(m.group(1))
                if found == expected:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                messages.append(
                    f"{rel}:{line_no}: MCP {label} drift '{m.group(0)}' "
                    f"(found={found}) does not match constants.json {key}={expected}"
                )

        pair_re, (k1, k2), pair_label = _MCP_COUNT_PAIR_PATTERN
        exp1 = payload.get(k1)
        exp2 = payload.get(k2)
        if isinstance(exp1, int) and isinstance(exp2, int):
            for m in pair_re.finditer(text):
                got1, got2 = int(m.group(1)), int(m.group(2))
                if got1 == exp1 and got2 == exp2:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                messages.append(
                    f"{rel}:{line_no}: MCP {pair_label} drift '{m.group(0)}' "
                    f"(found={got1} project + {got2} brain) does not match "
                    f"constants.json {k1}={exp1}, {k2}={exp2}"
                )
    return messages


def scan_test_counts(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return drift messages for cross-file test-count refs.

    Walks :data:`CROSS_FILE_SCAN_TARGETS`, strips fenced code blocks, and
    flags every match of :data:`_TEST_COUNT_PATTERNS` whose captured int does
    not match ``constants.json["test_count"]``. Patterns are narrow
    (badge URL, ``pytest suite (N tests)``, ``**N tests**``, badge label) to
    avoid noise on illustrative numbers in prose.
    """
    expected = payload.get("test_count")
    if not isinstance(expected, int):
        return []
    messages: list[str] = []
    for rel in CROSS_FILE_SCAN_TARGETS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))
        for pattern, label in _TEST_COUNT_PATTERNS:
            for m in pattern.finditer(text):
                found = int(m.group(1))
                if found == expected:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                messages.append(
                    f"{rel}:{line_no}: test-count drift '{m.group(0)}' "
                    f"({label}, found={found}) does not match "
                    f"constants.json test_count={expected}"
                )
    return messages


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def run_main(
    repo_root: Path,
    *,
    check: bool,
    skip_cross_files: bool = False,
    skip_mcp_counts: bool = False,
    skip_test_count: bool = False,
) -> int:
    path = output_json_path(repo_root)
    payload = build_constants_doc(repo_root)
    if check:
        if not path.is_file():
            print(f"Drift: missing {path} (run without --check to generate).", file=sys.stderr)
            return 1
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Drift: invalid JSON in {path}: {e}", file=sys.stderr)
            return 1
        if existing != payload:
            print(
                f"Drift: {path} does not match live pyproject / MCP tools / test count.\n"
                f"  expected tausik_version={payload.get('tausik_version')!r}\n"
                f"  Run: python scripts/gen_doc_constants.py",
                file=sys.stderr,
            )
            return 1
        if not skip_cross_files:
            cross_drift = scan_version_refs(repo_root, str(payload["tausik_version"]))
            if cross_drift:
                print("Cross-file version-ref drift:", file=sys.stderr)
                for msg in cross_drift:
                    print(f"  {msg}", file=sys.stderr)
                return 1
        if not skip_cross_files and not skip_mcp_counts:
            mcp_drift = scan_mcp_tool_counts(repo_root, payload)
            if mcp_drift:
                print("Cross-file MCP tool-count drift:", file=sys.stderr)
                for msg in mcp_drift:
                    print(f"  {msg}", file=sys.stderr)
                return 1
        if not skip_cross_files and not skip_test_count:
            test_drift = scan_test_counts(repo_root, payload)
            if test_drift:
                print("Cross-file test-count drift:", file=sys.stderr)
                for msg in test_drift:
                    print(f"  {msg}", file=sys.stderr)
                return 1
        print(f"OK — {path} matches repository constants.")
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(payload), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate docs/_generated/constants.json")
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if constants.json is missing or differs from code",
    )
    p.add_argument(
        "--skip-cross-files",
        action="store_true",
        help="Skip all cross-file scans (version refs, MCP tool counts, test count) — constants.json drift only",
    )
    p.add_argument(
        "--skip-mcp-counts",
        action="store_true",
        help="Skip the cross-file MCP tool-count scan (keep version-ref + test-count scans)",
    )
    p.add_argument(
        "--skip-test-count",
        action="store_true",
        help="Skip the cross-file test-count scan (keep version-ref + MCP-counts scans)",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: directory containing pyproject.toml)",
    )
    args = p.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    return run_main(
        root,
        check=args.check,
        skip_cross_files=args.skip_cross_files,
        skip_mcp_counts=args.skip_mcp_counts,
        skip_test_count=args.skip_test_count,
    )


if __name__ == "__main__":
    raise SystemExit(main())
