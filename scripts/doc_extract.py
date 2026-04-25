"""Optional document extraction via Microsoft markitdown.

Honors TAUSIK convention #19 (zero external deps): markitdown is **not** a
required dependency. Lazy-imported on first call; missing → graceful `None`.

Use case: DOCX / PPTX / XLSX / HTML / EPUB / audio / image conversion to
markdown. PDF is also supported but Claude Code's built-in `Read` tool
already handles PDFs well — prefer that for PDFs unless you need batch /
non-interactive extraction.

Install on demand: `pip install 'markitdown[all]'`.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def _import_markitdown() -> Any | None:
    """Lazy-import markitdown.MarkItDown. Returns class or None on missing."""
    try:
        from markitdown import MarkItDown  # type: ignore[import-not-found]
    except ImportError:
        return None
    return MarkItDown


def is_available() -> bool:
    """True iff markitdown is installed and importable."""
    return _import_markitdown() is not None


def extract_to_markdown(path: str, *, format_hint: str | None = None) -> str | None:
    """Convert a document at `path` to markdown via markitdown.

    Returns:
      str   — extracted markdown content (may be empty for image-only files)
      None  — markitdown not installed, path missing, or conversion failed.
              Diagnostic written to stderr in all None cases.

    Never raises: callers can fall back to other extraction paths or refuse
    silently. The `format_hint` arg is reserved for future per-format options
    (markitdown auto-detects today; the hint is logged but not yet enforced).
    """
    if not path or not isinstance(path, str):
        print("doc_extract: path is empty", file=sys.stderr)
        return None
    if not os.path.isfile(path):
        print(f"doc_extract: file not found: {path}", file=sys.stderr)
        return None

    cls = _import_markitdown()
    if cls is None:
        print(
            "doc_extract: markitdown not installed. "
            "Install with `pip install 'markitdown[all]'` to enable.",
            file=sys.stderr,
        )
        return None

    if format_hint:
        # Reserved for future per-format options (e.g. OCR toggles for images);
        # markitdown auto-detects today. Logged for diagnostics only.
        print(
            f"doc_extract: format_hint={format_hint!r} (logged, not yet enforced)",
            file=sys.stderr,
        )

    try:
        md = cls()
        result = md.convert(path)
    except Exception as e:  # noqa: BLE001
        print(f"doc_extract: markitdown failed on {path}: {e}", file=sys.stderr)
        return None

    text_content = getattr(result, "text_content", None)
    if text_content is None:
        # markitdown's API stable on .text_content; handle older shape too
        text_content = getattr(result, "markdown", None)
    if not isinstance(text_content, str):
        print(
            f"doc_extract: unexpected markitdown result shape: {type(result)!r}",
            file=sys.stderr,
        )
        return None
    return text_content
