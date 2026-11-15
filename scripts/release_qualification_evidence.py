"""Shared limits and bounded file reads for untrusted qualification evidence."""

from __future__ import annotations

from pathlib import Path


MAX_EVIDENCE_BYTES = 32 * 1024 * 1024


def read_bounded_file(path: str | Path, *, max_bytes: int = MAX_EVIDENCE_BYTES) -> bytes:
    """Read at most ``max_bytes`` and reject artifacts that exceed the limit."""
    target = Path(path)
    if target.stat().st_size > max_bytes:
        raise ValueError("qualification evidence exceeds the byte limit")
    with target.open("rb") as stream:
        payload = stream.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("qualification evidence exceeds the byte limit")
    return payload
