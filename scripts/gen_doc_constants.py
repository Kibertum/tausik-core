"""Generate `docs/_generated/constants.json` from pyproject + MCP tool counts.

Usage:
  python scripts/gen_doc_constants.py                      # write / update file
  python scripts/gen_doc_constants.py --check              # exit 1 on drift (constants.json + cross-file refs)
  python scripts/gen_doc_constants.py --check --skip-cross-files
                                                            # exit 1 on constants.json drift only (legacy)
  python scripts/gen_doc_constants.py --check --skip-mcp-counts
                                                            # exit 1 on constants + version refs only (skip MCP counts)

Also available as: ``tausik doc constants [--check]``.

The cross-file scanners (version refs, MCP tool counts, test counts, repo-state
counts) live in :mod:`doc_drift_scanners` and are re-exported here for backward
compatibility. constants.json also carries ``mcp_descriptions_hash`` so editing
a client-visible MCP tool description fails ``--check`` until the file is
regenerated (an explicit acknowledgement of the cache-busting change).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from code_counts import code_counts_flat
from doc_drift_scanners import (
    CROSS_FILE_SCAN_TARGETS,
    scan_code_counts,
    scan_mcp_tool_counts,
    scan_py_version_constants,
    scan_test_counts,
    scan_version_refs,
)
from mcp_tool_counts import mcp_counts_flat, mcp_descriptions_digest
from pytest_test_count import count_tests

__all__ = [
    "CROSS_FILE_SCAN_TARGETS",
    "build_constants_doc",
    "main",
    "output_json_path",
    "run_main",
    "scan_code_counts",
    "scan_mcp_tool_counts",
    "scan_py_version_constants",
    "scan_test_counts",
    "scan_version_refs",
]


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
    payload.update(code_counts_flat(repo_root))
    payload["mcp_descriptions_hash"] = mcp_descriptions_digest(repo_root)
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


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _report_drift(label: str, messages: list[str]) -> None:
    print(label, file=sys.stderr)
    for msg in messages:
        print(f"  {msg}", file=sys.stderr)


def run_main(
    repo_root: Path,
    *,
    check: bool,
    skip_cross_files: bool = False,
    skip_mcp_counts: bool = False,
    skip_test_count: bool = False,
    skip_code_counts: bool = False,
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
                _report_drift("Cross-file version-ref drift:", cross_drift)
                return 1
            py_ver_drift = scan_py_version_constants(repo_root, str(payload["tausik_version"]))
            if py_ver_drift:
                _report_drift("Python __version__ drift:", py_ver_drift)
                return 1
        if not skip_cross_files and not skip_mcp_counts:
            mcp_drift = scan_mcp_tool_counts(repo_root, payload)
            if mcp_drift:
                _report_drift("Cross-file MCP tool-count drift:", mcp_drift)
                return 1
        if not skip_cross_files and not skip_test_count:
            test_drift = scan_test_counts(repo_root, payload)
            if test_drift:
                _report_drift("Cross-file test-count drift:", test_drift)
                return 1
        if not skip_cross_files and not skip_code_counts:
            code_drift = scan_code_counts(repo_root, payload)
            if code_drift:
                _report_drift("Cross-file repo-state count drift:", code_drift)
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
        "--skip-code-counts",
        action="store_true",
        help="Skip the cross-file repo-state count scan (stacks / hooks / review agents)",
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
        skip_code_counts=args.skip_code_counts,
    )


if __name__ == "__main__":
    raise SystemExit(main())
