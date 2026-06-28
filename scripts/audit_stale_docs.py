"""Static stale-docs audit (v14-audit-stale-docs).

Reports markdown files inside ``docs/`` that **no other tracked file
references** — candidates for review (NOT auto-delete). The detector is
deliberately conservative: roots, language indices, README, archived
research, and the EN/RU mirror partner of any referenced doc all stay
out of the report.

Run::

    python scripts/audit_stale_docs.py            # markdown report
    python scripts/audit_stale_docs.py --json     # JSON output
    python scripts/audit_stale_docs.py --check    # exit 1 if stale found

Spec / motivation: docs/ru/research/tausik-1.4-epics-master-plan-2026-05-01.md
(epic ``v14-dead-code-audit``).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path

# Files that are roots / always considered referenced even when nothing
# links to them (entry points, READMEs, generated artifacts, archives).
ROOT_DOCS: tuple[str, ...] = (
    "docs/README.md",
    "docs/en/index.md",
    "docs/ru/index.md",
    "docs/_generated/README.md",
    "docs/en/release-notes.md",
    "docs/ru/release-notes.md",
)

# Glob excludes — paths inside these are NOT reported even if unreferenced.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    "docs/_generated/*",
    "docs/_generated/**/*",
    "docs/en/research/*",
    "docs/ru/research/*",
    "docs/en/release-notes/*",
    "docs/ru/release-notes/*",
)

# Where to look for inbound references (files that may link into docs/).
INBOUND_DIRS: tuple[str, ...] = (
    "harness",
    "bootstrap",
    "scripts",
    "tests",
    "docs",
    ".",
)

# File extensions whose contents we scan for doc references.
INBOUND_GLOBS: tuple[str, ...] = ("*.md", "*.py", "*.json", "*.toml", "*.yaml", "*.yml")

# Top-level markdown / text files at repo root that count as inbound link sources.
ROOT_FILES: tuple[str, ...] = (
    "README.md",
    "README.ru.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CHANGELOG.md",
    "CHANGELOG.ru.md",
    "QWEN.md",
    "AUDIT.md",
)


def _is_excluded(rel: str, excludes: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in excludes)


def _mirror_partner(rel: str) -> str | None:
    """`docs/en/foo.md` ↔ `docs/ru/foo.md`. Returns the partner path or None."""
    if rel.startswith("docs/en/"):
        return "docs/ru/" + rel[len("docs/en/") :]
    if rel.startswith("docs/ru/"):
        return "docs/en/" + rel[len("docs/ru/") :]
    return None


def _doc_files(repo_root: Path, excludes: tuple[str, ...]) -> list[str]:
    docs_dir = repo_root / "docs"
    if not docs_dir.is_dir():
        return []
    out: list[str] = []
    for p in docs_dir.rglob("*.md"):
        rel = p.relative_to(repo_root).as_posix()
        if _is_excluded(rel, excludes):
            continue
        out.append(rel)
    return sorted(out)


def _gather_inbound_text(repo_root: Path) -> str:
    """Concatenate file contents that may reference docs/ paths.

    Cheaper to do one big grep-like substring search than per-pair regex.
    """
    chunks: list[str] = []
    seen: set[Path] = set()
    for d in INBOUND_DIRS:
        if d == ".":
            for fname in ROOT_FILES:
                p = repo_root / fname
                if p.is_file() and p not in seen:
                    seen.add(p)
                    try:
                        chunks.append(p.read_text(encoding="utf-8"))
                    except (UnicodeDecodeError, OSError):
                        continue
            continue
        sub = repo_root / d
        if not sub.is_dir():
            continue
        for pattern in INBOUND_GLOBS:
            for p in sub.rglob(pattern):
                if p in seen:
                    continue
                seen.add(p)
                try:
                    chunks.append(p.read_text(encoding="utf-8"))
                except (UnicodeDecodeError, OSError):
                    continue
    return "\n".join(chunks)


def _basename_needles(rel: str) -> list[str]:
    """Substrings that count as a reference to ``rel``."""
    base = rel.split("/")[-1]
    short = base[:-3] if base.endswith(".md") else base
    return [rel, "/" + base, "(" + base + ")", short + ".md"]


def collect_stale(
    repo_root: Path,
    excludes: tuple[str, ...] = DEFAULT_EXCLUDES,
) -> list[str]:
    docs = _doc_files(repo_root, excludes)
    if not docs:
        return []

    haystack = _gather_inbound_text(repo_root)
    referenced: set[str] = set(ROOT_DOCS)
    for rel in docs:
        if rel in referenced:
            continue
        if any(needle in haystack for needle in _basename_needles(rel)):
            referenced.add(rel)

    # Mirror partner: if foo.md is referenced, treat its EN/RU twin as referenced too.
    for rel in list(referenced):
        twin = _mirror_partner(rel)
        if twin and twin in docs:
            referenced.add(twin)

    return sorted(rel for rel in docs if rel not in referenced)


def render_markdown(stale: list[str], excludes: tuple[str, ...]) -> str:
    lines = ["# Stale-docs audit (`docs/`)\n"]
    if not stale:
        lines.append("No stale docs detected. (OK)\n")
    else:
        lines.append(
            f"{len(stale)} candidate(s) — **manual review required**, never auto-delete:\n"
        )
        for rel in stale:
            lines.append(f"- `{rel}`")
        lines.append("")
    lines.append("## Stale criteria\n")
    lines.append(
        "- File lives under `docs/` but no path/basename match was found in tracked sources."
    )
    lines.append("- Mirror partners (EN <-> RU) are reciprocally referenced.")
    lines.append("- Research and release-notes archives are excluded by glob.")
    lines.append("")
    lines.append("## Excluded glob patterns\n")
    for pat in excludes:
        lines.append(f"- `{pat}`")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Static stale-docs audit (docs/)")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any stale doc is found (useful for CI)",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: directory containing pyproject.toml)",
    )
    args = p.parse_args(argv)

    if args.repo_root:
        root = Path(args.repo_root).resolve()
    else:
        here = Path.cwd().resolve()
        root = next(
            (q for q in [here, *here.parents] if (q / "pyproject.toml").is_file()),
            here,
        )

    stale = collect_stale(root)
    if args.json:
        print(
            json.dumps(
                {"stale": stale, "excludes": list(DEFAULT_EXCLUDES), "roots": list(ROOT_DOCS)},
                indent=2,
            )
        )
    else:
        print(render_markdown(stale, DEFAULT_EXCLUDES))

    if args.check and stale:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
