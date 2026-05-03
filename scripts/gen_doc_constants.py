"""Generate `docs/_generated/constants.json` from pyproject + MCP tool counts.

Usage:
  python scripts/gen_doc_constants.py           # write / update file
  python scripts/gen_doc_constants.py --check   # exit 1 on drift

Also available as: ``tausik doc constants [--check]``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcp_tool_counts import mcp_counts_flat


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


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def run_main(repo_root: Path, *, check: bool) -> int:
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
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: directory containing pyproject.toml)",
    )
    args = p.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    return run_main(root, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
