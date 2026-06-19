"""Qwen Code provider (Decision #119, axis-1) — stub.

Active-model detection not yet wired; returns None ("unknown"). Present so the
registry contract and `--ide qwen` bootstrap have a home to grow into.
"""

from __future__ import annotations

from . import register
from .base import Provider


class QwenProvider(Provider):
    def name(self) -> str:
        return "qwen"

    def get_transcript_path(self) -> str | None:
        return None

    def get_active_model(self) -> str | None:
        return None


def _register_self() -> None:
    register(QwenProvider())
