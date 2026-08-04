"""Compact hierarchical rollup of verbose command output (tool-output-rollup).

Borrowed from cubest: instead of dumping N lines, collapse them into a
dimensions-keyed aggregate with budget knobs (top_n / min_count / max_lines), so
an agent reading a large audit log or a big epic's task list pays a bounded token
cost. Presentation only — the underlying data, schema and semantics are
untouched, and `--full` on the command always bypasses this to the exact prior
output.

Three rules keep it honest:
  - DETERMINISTIC order: groups sort by (count desc, then key asc) — same input,
    same lines, every run.
  - Never hide silently: whenever a knob drops rows, the footer prints the
    DENOMINATOR — how many groups and rows are NOT shown — so the reader knows the
    view is partial. A rollup that swallowed the tail without saying so would be
    worse than the dump it replaces.
  - No collapse below threshold: when the input is small enough that a rollup
    saves nothing, `should_rollup` returns False and the caller prints the full
    output unchanged. The rollup exists to cut tokens, not to hide data.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Sequence

try:  # argparse is stdlib, but keep the core importable even if a caller stubs it
    import argparse
except ImportError:  # pragma: no cover - argparse is always present
    argparse = None  # type: ignore[assignment]


def add_rollup_flags(parser: "argparse.ArgumentParser") -> None:
    """Attach the shared rollup budget flags to a verbose command's parser.

    `--full` bypasses the rollup to the exact prior output; `--top-n` /
    `--max-lines` cap how many group lines print when a rollup IS rendered.
    """
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print the full (un-rolled) output, exactly as before rollup existed.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        dest="top_n",
        help="When rolled up, show only the top-N groups (a denominator footer names the rest).",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=None,
        dest="max_lines",
        help="When rolled up, cap the number of group lines (stricter of this and --top-n wins).",
    )


# Below this many rows a rollup saves little and only costs the reader the detail
# they came for, so the caller prints the full output. Chosen above the size of
# ordinary test/CLI fixtures so small outputs stay byte-identical to the prior
# behavior; only genuinely large logs/lists collapse.
DEFAULT_THRESHOLD = 25


def should_rollup(n_rows: int, *, full: bool, threshold: int = DEFAULT_THRESHOLD) -> bool:
    """Whether to render a rollup instead of the full dump.

    `--full` always wins (never rollup). Below `threshold` there is nothing to
    save, so the caller renders the full output unchanged.
    """
    if full:
        return False
    return n_rows >= threshold


def _default_key(dimensions: Sequence[str]) -> Callable[[dict[str, Any]], tuple[str, ...]]:
    def key_fn(row: dict[str, Any]) -> tuple[str, ...]:
        return tuple(str(row.get(d, "") or "") for d in dimensions)

    return key_fn


def render_rollup(
    rows: Sequence[dict[str, Any]],
    dimensions: Sequence[str],
    *,
    title: str,
    key_fn: Callable[[dict[str, Any]], tuple[str, ...]] | None = None,
    top_n: int | None = None,
    min_count: int = 1,
    max_lines: int | None = None,
) -> list[str]:
    """Collapse `rows` into a deterministic aggregate keyed by `dimensions`.

    Each output line is ``<count>  <dim1 / dim2 / ...>``. Budget knobs:
      - ``min_count``: hide groups whose count is below this (noise floor).
      - ``top_n`` / ``max_lines``: cap how many group lines print (the stricter
        of the two applies when both are set).
    Every hidden group and row is accounted for in a denominator footer.
    """
    total = len(rows)
    kf = key_fn or _default_key(dimensions)
    counter: Counter[tuple[str, ...]] = Counter()
    for row in rows:
        counter[kf(row)] += 1
    total_groups = len(counter)

    # Deterministic: most frequent first, ties broken by key ascending.
    ordered = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    kept = [(k, c) for k, c in ordered if c >= min_count]

    limit: int | None = None
    for cap in (top_n, max_lines):
        if cap is not None:
            limit = cap if limit is None else min(limit, cap)
    shown = kept if limit is None else kept[: max(limit, 0)]

    shown_rows = sum(c for _, c in shown)
    hidden_groups = total_groups - len(shown)
    hidden_rows = total - shown_rows

    header = f"{title} — {total} rows in {total_groups} group(s) (rollup; --full for detail):"
    lines = [header]
    for key, count in shown:
        lines.append(f"  {count:>6}  {' / '.join(key)}")
    if hidden_groups > 0:
        floor = f", min_count={min_count}" if min_count > 1 else ""
        lines.append(f"  … {hidden_groups} more group(s), {hidden_rows} row(s) not shown{floor}")
    return lines
