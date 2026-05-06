"""Generate `docs/_generated/constants.json` from pyproject + MCP tool counts.

Usage:
  python scripts/gen_doc_constants.py                      # write / update file
  python scripts/gen_doc_constants.py --check              # exit 1 on drift (constants.json + cross-file refs)
  python scripts/gen_doc_constants.py --check --skip-cross-files
                                                            # exit 1 on constants.json drift only (legacy)

Also available as: ``tausik doc constants [--check]``.

Cross-file scan walks README.md, README.ru.md, AGENTS.md, CLAUDE.md,
docs/en/architecture.md, docs/ru/architecture.md and verifies every
``vX.Y`` / ``vX.Y.Z`` version ref outside fenced code blocks against
``constants.json["tausik_version"]``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from mcp_tool_counts import mcp_counts_flat

_VERSION_RE = re.compile(r"\bv(\d+)\.(\d+)(?:\.(\d+))?(?:\.x)?\b")
_FENCED_BLOCK_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

CROSS_FILE_SCAN_TARGETS: tuple[str, ...] = (
    "README.md",
    "README.ru.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/en/architecture.md",
    "docs/ru/architecture.md",
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
    """Canonical payload written to ``constants.json``."""
    payload: dict[str, object] = {
        "schema_version": 1,
        "tausik_version": read_project_version(repo_root),
    }
    counts = mcp_counts_flat(repo_root)
    payload.update(counts)
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


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def run_main(repo_root: Path, *, check: bool, skip_cross_files: bool = False) -> int:
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
                f"Drift: {path} does not match live pyproject / MCP tools.\n"
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
        help="Skip the cross-file version-ref scan (constants.json drift only)",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: directory containing pyproject.toml)",
    )
    args = p.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    return run_main(root, check=args.check, skip_cross_files=args.skip_cross_files)


if __name__ == "__main__":
    raise SystemExit(main())
