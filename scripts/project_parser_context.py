"""argparse for `tausik context` and `update-claudemd` projection commands."""

from __future__ import annotations

from typing import Any


def build_context_subparsers(sub: Any) -> None:
    uc_p = sub.add_parser(
        "update-claudemd",
        help="Refresh DYNAMIC section of CLAUDE.md only (Claude adapter). "
        "Prefer `context refresh --target` for other hosts.",
    )
    uc_p.add_argument(
        "--claudemd", default=None, help="Path to CLAUDE.md (auto-detected if omitted)"
    )
    uc_p.add_argument(
        "--sibling",
        action="store_true",
        help="Also refresh AGENTS.md when it carries DYNAMIC markers "
        "(off by default; hand-maintained AGENTS.md is never overwritten)",
    )
    uc_p.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Show diff; do not modify. Exit 0 if identical, 1 if drift.",
    )

    ctx_p = sub.add_parser(
        "context",
        help="Host-neutral session/task projections into instruction files",
    )
    ctx_sub = ctx_p.add_subparsers(dest="context_cmd")
    ctx_r = ctx_sub.add_parser(
        "refresh",
        help="Apply DYNAMIC state to one explicit --target (required)",
    )
    ctx_r.add_argument(
        "--target",
        required=False,
        default=None,
        help="Projection target: claude, cursor, agents, kilo, codex, qwen, …",
    )
    ctx_r.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Show whether the target would change; do not write",
    )
