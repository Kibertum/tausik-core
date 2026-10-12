"""Cursor provider (Decision #119, axis-1) — stub.

Cursor active-model detection is not yet wired; returns None ("unknown") so the
banner falls back to recommendation-only. Present so `--ide cursor` bootstrap
and the registry contract have a home to grow into.
"""

from __future__ import annotations

from . import register
from .base import Provider


class CursorProvider(Provider):
    def name(self) -> str:
        return "cursor"

    def get_transcript_path(self) -> str | None:
        return None

    def get_active_model(self) -> str | None:
        return None


def _register_self() -> None:
    register(CursorProvider())
