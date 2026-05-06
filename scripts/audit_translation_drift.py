"""Translation-drift audit (v14b-junk-translation-drift-audit).

Reports structural drift between EN/RU mirror docs (``docs/en/foo.md`` ↔
``docs/ru/foo.md``). Compares three coarse metrics per pair:

- ATX heading count (``#``..``######`` lines, **outside fenced code blocks**)
- Fenced code-block count (lines starting with three backticks)
- Markdown-table count (separator rows like ``|---|---|``)

Pairs whose EN or RU side carries
``<!-- audit-translation-drift: skip -->`` are listed under
"Intentionally abbreviated" rather than counted as drift — use this marker
on RU summaries that explicitly point readers to the long-form EN doc.

Not a semantic / NLP comparison — surfaces stale RU mirrors after EN edits
without blocking commits. Pattern follows ``scripts/audit_stale_docs.py``
(same arg layout, same ``--check`` semantic, same Path discovery).

Run::

    python scripts/audit_translation_drift.py            # markdown report
    python scripts/audit_translation_drift.py --json     # JSON output
    python scripts/audit_translation_drift.py --check    # exit 1 if drift found
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

EN_DIR = "docs/en"
RU_DIR = "docs/ru"

_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)
_CODE_FENCE_RE = re.compile(r"^\s*```", re.MULTILINE)
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s\-:|]+\|\s*$", re.MULTILINE)
_SKIP_MARKER_RE = re.compile(r"<!--\s*audit-translation-drift:\s*skip\s*-->")
_FENCED_BLOCK_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


class Metrics(NamedTuple):
    headings: int
    code_blocks: int
    tables: int

    def as_dict(self) -> dict[str, int]:
        return {
            "headings": self.headings,
            "code_blocks": self.code_blocks,
            "tables": self.tables,
        }


class Drift(NamedTuple):
    basename: str
    en: Metrics
    ru: Metrics

    def deltas(self) -> dict[str, int]:
        return {
            "headings": self.en.headings - self.ru.headings,
            "code_blocks": (self.en.code_blocks // 2) - (self.ru.code_blocks // 2),
            "tables": self.en.tables - self.ru.tables,
        }

    def has_drift(self) -> bool:
        return any(d != 0 for d in self.deltas().values())


def _strip_fenced_blocks(text: str) -> str:
    """Remove fenced code blocks (between triple backticks) before heading counting.

    Headings *inside* code fences are markdown examples (e.g. ``# BAD`` lines
    inside a `` ```markdown ... ``` `` block), not real document sections, so
    they must not contribute to structural drift. Fences themselves and any
    table separators inside them are still counted via the unmodified text.
    """
    return _FENCED_BLOCK_RE.sub("", text)


def count_metrics(text: str) -> Metrics:
    """Count structural markers in markdown text.

    Headings are counted only OUTSIDE fenced code blocks. Code-block fences
    and table separators are counted on the raw text. ``code_blocks`` is
    raw fence-line occurrences; pairs (open+close) are normalized to a
    logical block count via integer-divide-by-2 inside :meth:`Drift.deltas`
    so an unmatched fence on one side still surfaces.
    """
    text_no_fences = _strip_fenced_blocks(text)
    return Metrics(
        headings=len(_HEADING_RE.findall(text_no_fences)),
        code_blocks=len(_CODE_FENCE_RE.findall(text)),
        tables=len(_TABLE_SEP_RE.findall(text)),
    )


def has_skip_marker(text: str) -> bool:
    """True if the doc carries ``<!-- audit-translation-drift: skip -->``.

    The marker opts a pair out of structural-drift checks. Use it on
    intentionally-abbreviated mirrors that explicitly point readers to the
    full version (e.g. RU summaries that link out to the long-form EN doc).
    """
    return bool(_SKIP_MARKER_RE.search(text))


def _list_basenames(dir_path: Path) -> set[str]:
    if not dir_path.is_dir():
        return set()
    return {p.name for p in dir_path.glob("*.md")}


def _pair_files(
    repo_root: Path,
) -> tuple[list[str], list[str], list[str]]:
    """Return (paired, en_only, ru_only) basenames sorted alphabetically."""
    en_names = _list_basenames(repo_root / EN_DIR)
    ru_names = _list_basenames(repo_root / RU_DIR)
    paired = sorted(en_names & ru_names)
    en_only = sorted(en_names - ru_names)
    ru_only = sorted(ru_names - en_names)
    return paired, en_only, ru_only


def audit_pairs(
    repo_root: Path,
) -> tuple[list[Drift], list[str], list[str], list[str]]:
    """Compare every paired basename. Returns ``(drifts, en_only, ru_only, abbreviated)``.

    ``abbreviated`` lists basenames where either side carries the skip marker
    — those pairs are NOT counted as drift even when their structural metrics
    differ.
    """
    paired, en_only, ru_only = _pair_files(repo_root)
    drifts: list[Drift] = []
    abbreviated: list[str] = []
    for name in paired:
        en_text = (repo_root / EN_DIR / name).read_text(encoding="utf-8")
        ru_text = (repo_root / RU_DIR / name).read_text(encoding="utf-8")
        if has_skip_marker(en_text) or has_skip_marker(ru_text):
            abbreviated.append(name)
            continue
        d = Drift(basename=name, en=count_metrics(en_text), ru=count_metrics(ru_text))
        if d.has_drift():
            drifts.append(d)
    return drifts, en_only, ru_only, abbreviated


def render_markdown(
    drifts: list[Drift],
    en_only: list[str],
    ru_only: list[str],
    abbreviated: list[str] | None = None,
) -> str:
    abbreviated = abbreviated or []
    lines = ["# Translation-drift audit (`docs/en` ↔ `docs/ru`)\n"]
    if not drifts:
        lines.append("No structural drift detected on paired mirrors. (OK)\n")
    else:
        lines.append(
            f"{len(drifts)} pair(s) with structural drift "
            "— **EN edits likely landed without RU mirror update**:\n"
        )
        lines.append("| Pair | Δ headings | Δ code-blocks | Δ tables |")
        lines.append("|------|-----------:|--------------:|---------:|")
        for d in drifts:
            deltas = d.deltas()
            lines.append(
                f"| `{d.basename}` | {deltas['headings']:+d} "
                f"| {deltas['code_blocks']:+d} | {deltas['tables']:+d} |"
            )
        lines.append("")
        lines.append(
            "Δ = EN − RU. Positive = EN has more (RU mirror likely lagging "
            "behind a recent EN edit); negative = RU has more."
        )
        lines.append("")
    if abbreviated:
        lines.append("## Intentionally abbreviated (skip marker present)\n")
        lines.append(
            f"{len(abbreviated)} pair(s) carry "
            "`<!-- audit-translation-drift: skip -->` — not counted as drift:"
        )
        lines.append(", ".join("`" + n + "`" for n in abbreviated))
        lines.append("")
    if en_only or ru_only:
        lines.append("## Unpaired files (informational, not drift)\n")
        if en_only:
            lines.append(f"EN-only ({len(en_only)}): {', '.join('`' + n + '`' for n in en_only)}")
        if ru_only:
            lines.append(f"RU-only ({len(ru_only)}): {', '.join('`' + n + '`' for n in ru_only)}")
        lines.append("")
    lines.append("## Methodology\n")
    lines.append(
        "- Compares ATX heading count, fenced-code-block count, and markdown-table-separator count."
    )
    lines.append(
        "- Headings inside fenced code blocks (`# BAD` / `# GOOD` examples in `````markdown` fences) are excluded."
    )
    lines.append(
        "- Files carrying `<!-- audit-translation-drift: skip -->` are listed under 'Intentionally abbreviated' and excluded from drift counting."
    )
    lines.append(
        "- Structural only: no word-by-word translation check, no NLP, no semantic comparison."
    )
    lines.append(
        "- Default mode is advisory (always exit 0). `--check` exits 1 only when paired drift exists."
    )
    return "\n".join(lines) + "\n"


def render_json(
    drifts: list[Drift],
    en_only: list[str],
    ru_only: list[str],
    abbreviated: list[str] | None = None,
) -> str:
    payload = {
        "drifts": [
            {
                "basename": d.basename,
                "en": d.en.as_dict(),
                "ru": d.ru.as_dict(),
                "deltas": d.deltas(),
            }
            for d in drifts
        ],
        "en_only": en_only,
        "ru_only": ru_only,
        "abbreviated": abbreviated or [],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Translation-drift audit (docs/en ↔ docs/ru, structural only)"
    )
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any paired pair has structural drift (CI mode)",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: directory containing pyproject.toml)",
    )
    args = p.parse_args(argv)

    # Windows default stdout is cp1252; report uses ↔/Δ + Cyrillic basenames.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.repo_root:
        root = Path(args.repo_root).resolve()
    else:
        here = Path.cwd().resolve()
        root = next(
            (q for q in [here, *here.parents] if (q / "pyproject.toml").is_file()),
            here,
        )

    drifts, en_only, ru_only, abbreviated = audit_pairs(root)
    print(
        render_json(drifts, en_only, ru_only, abbreviated)
        if args.json
        else render_markdown(drifts, en_only, ru_only, abbreviated)
    )

    if args.check and drifts:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
